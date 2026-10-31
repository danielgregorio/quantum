//! The machine that runs a world's expressions as bytecode (PLAN_WORLD_ENGINE.md, E2), with the meaning of the
//! Core's interpreter (quantum/core/expressions.py) to the value. The compiler is Python's
//! (quantum/runtime/gameserver/bytecode.py); its instructions are a stack machine's.
//!
//! What the Core means, and the machine with it:
//! - a text that reads as a number is a number in arithmetic and comparison (`'5' + 3` is 8, `'10' > '9'`);
//! - `+` adds numbers or joins two texts or two lists; the rest of arithmetic is on numbers alone (a bool is not);
//! - `/` is a float, `//` floors and `%` takes the divisor's sign, as Python's; `**` refuses what is too large;
//! - `and` and `or` give an operand, `not` a bool, a chain of comparisons stops at the first that fails;
//! - `in` compares as `==` does; a record's missing key and a list's missing index are errors, not null;
//! - `round` goes half away from zero over the number's text (`round(2.5)` is 3).
//!
//! A whole number is 64 bits here (Python's have no end): past that, the machine refuses by name. A world's own
//! functions, and its entities' fields, are its host's: the machine asks.

use std::cmp::Ordering;
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering::Relaxed};
use std::sync::Arc;

use crate::value::{py_eq, write_float, Map, Value};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Op {
    Const,
    Name,
    Attr,
    Index,
    Slice,
    BinOp,
    Unary,
    Compare,
    Jump,
    JumpIfFalse,
    JumpIfFalseOrPop,
    JumpIfTrueOrPop,
    Dup,
    Rot2,
    Rot3,
    Pop,
    List,
    Tuple,
    Dict,
    Call,
    CallHost,
    CallKw,
    CallHostKw,
    StoreName,
    StorePath,
    Format,
    LoopItems,
    LoopRange,
    ForNext,
    CallUser,
    CallStatement,
    Return,
    Refuse,
    Effect,
    Line,
    LocalOrNull,
    Fail,
}

/// The instructions' names, in their numbers' order: bytecode.py's OPCODES.
pub const OPCODES: [&str; 37] = [
    "CONST",
    "NAME",
    "ATTR",
    "INDEX",
    "SLICE",
    "BINOP",
    "UNARY",
    "COMPARE",
    "JUMP",
    "JUMP_IF_FALSE",
    "JUMP_IF_FALSE_OR_POP",
    "JUMP_IF_TRUE_OR_POP",
    "DUP",
    "ROT2",
    "ROT3",
    "POP",
    "LIST",
    "TUPLE",
    "DICT",
    "CALL",
    "CALL_HOST",
    "CALL_KW",
    "CALL_HOST_KW",
    "STORE_NAME",
    "STORE_PATH",
    "FORMAT",
    "LOOP_ITEMS",
    "LOOP_RANGE",
    "FOR_NEXT",
    "CALL_USER",
    "CALL_STATEMENT",
    "RETURN",
    "REFUSE",
    "EFFECT",
    "LINE",
    "LOCAL_OR_NULL",
    "FAIL",
];

/// A loop with no index= (the compiler's NO_INDEX).
pub const NO_INDEX: u32 = 0xFFFF_FFFF;
/// What a tick's loop may turn, and how deep q:functions may call (rules.py's MAX_LOOP, MAX_DEPTH).
pub const MAX_LOOP: usize = 100_000;
pub const MAX_DEPTH: usize = 64;

impl Op {
    pub fn from_number(n: i64) -> Option<Op> {
        const ALL: [Op; 37] = [
            Op::Const,
            Op::Name,
            Op::Attr,
            Op::Index,
            Op::Slice,
            Op::BinOp,
            Op::Unary,
            Op::Compare,
            Op::Jump,
            Op::JumpIfFalse,
            Op::JumpIfFalseOrPop,
            Op::JumpIfTrueOrPop,
            Op::Dup,
            Op::Rot2,
            Op::Rot3,
            Op::Pop,
            Op::List,
            Op::Tuple,
            Op::Dict,
            Op::Call,
            Op::CallHost,
            Op::CallKw,
            Op::CallHostKw,
            Op::StoreName,
            Op::StorePath,
            Op::Format,
            Op::LoopItems,
            Op::LoopRange,
            Op::ForNext,
            Op::CallUser,
            Op::CallStatement,
            Op::Return,
            Op::Refuse,
            Op::Effect,
            Op::Line,
            Op::LocalOrNull,
            Op::Fail,
        ];
        usize::try_from(n).ok().and_then(|i| ALL.get(i).copied())
    }
}

/// An expression compiled: instructions (op, a, b), constants and names.
#[derive(Clone, Debug)]
pub struct Code {
    pub ops: Vec<(Op, u32, u32)>,
    pub consts: Vec<Value>,
    pub names: Vec<String>,
}

impl Code {
    /// Checks every jump, constant and name an instruction points at, once, so running it cannot go out of bounds.
    pub fn check(&self) -> Result<(), String> {
        for (i, (op, a, b)) in self.ops.iter().enumerate() {
            let (a, b) = (*a as usize, *b as usize);
            let names = self.names.len();
            let ok = match op {
                Op::Const | Op::Effect | Op::Fail => a < self.consts.len(),
                Op::Name
                | Op::Attr
                | Op::Call
                | Op::CallHost
                | Op::StoreName
                | Op::CallUser
                | Op::CallStatement
                | Op::LocalOrNull => a < names,
                Op::StorePath => a < self.consts.len() && b < self.consts.len(),
                Op::LoopItems | Op::LoopRange => a < names && (b == NO_INDEX as usize || b < names),
                Op::CallKw | Op::CallHostKw => a < names && b < self.consts.len(),
                Op::Jump
                | Op::JumpIfFalse
                | Op::JumpIfFalseOrPop
                | Op::JumpIfTrueOrPop
                | Op::ForNext => a <= self.ops.len(),
                Op::BinOp => a < 7,
                Op::Unary => a < 3,
                Op::Compare => a < 8,
                _ => true,
            };
            if !ok {
                return Err(format!("instruction {i} points out of the code"));
            }
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ErrorKind {
    /// A name, key, index or attribute that is not there (the Core's UndefinedError).
    Undefined,
    /// Anything else an expression cannot do (ExpressionError).
    Expression,
    /// A rule that could not run (rules.py's RuleError): a loop that is not of a list, a call too deep...
    Rule,
    /// A command the world says no to (Refused): a q:require that did not hold.
    Refused,
    /// What the host raised (a world's own refusal or error): the host keeps it, to raise as it was.
    Host,
    /// What Python itself raises there (int() of a text that is not a number, in a q:loop from=): the world does
    /// not catch it, and neither does the machine.
    Python(Raise),
}

/// Python's own exceptions, for ErrorKind::Python.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Raise {
    Type,
    Value,
    Overflow,
}

#[derive(Clone, Debug)]
pub struct VmError {
    pub kind: ErrorKind,
    pub message: String,
    /// The line of the statement it came from: None until the block it ran in says (Some(0): a statement with no
    /// line).
    pub line: Option<u32>,
}

impl VmError {
    pub fn new(kind: ErrorKind, message: impl Into<String>) -> VmError {
        VmError {
            kind,
            message: message.into(),
            line: None,
        }
    }

    /// As Python says the error it is: a RuleError with its line ("line 12: ..."), the others as they are.
    pub fn text(&self) -> String {
        match self.kind {
            ErrorKind::Rule | ErrorKind::Expression | ErrorKind::Undefined => match self.line {
                Some(line) if line > 0 => format!("line {line}: {}", self.message),
                _ => self.message.clone(),
            },
            _ => self.message.clone(),
        }
    }
}

fn err<T>(message: impl Into<String>) -> Result<T, VmError> {
    Err(VmError::new(ErrorKind::Expression, message))
}

fn undefined<T>(message: impl Into<String>) -> Result<T, VmError> {
    Err(VmError::new(ErrorKind::Undefined, message))
}

fn rule<T>(message: impl Into<String>) -> Result<T, VmError> {
    Err(VmError::new(ErrorKind::Rule, message))
}

fn raise<T>(kind: Raise, message: impl Into<String>) -> Result<T, VmError> {
    Err(VmError::new(ErrorKind::Python(kind), message))
}

/// What the machine asks the world: its variables, its entities' fields, its functions.
pub trait Host {
    /// A variable of the world (after the block's own); None: there is none.
    fn variable(&mut self, name: &str) -> Option<Value>;
    /// An entity's field: None when it has no such field.
    fn field(&mut self, id: &str, key: &str) -> Result<Option<Value>, VmError>;
    /// An entity's fields' names, in order.
    fn keys(&mut self, id: &str) -> Result<Vec<String>, VmError>;
    /// A world's function, or a q:function the machine does not hold.
    fn call(
        &mut self,
        name: &str,
        args: Vec<Value>,
        kwargs: Vec<(String, Value)>,
    ) -> Result<Value, VmError>;
    /// q:set of a world's variable: false when the world has none of that name (the block's own, then).
    fn write_var(&mut self, _name: &str, _value: &Value, _line: u32) -> Result<bool, VmError> {
        Ok(false)
    }
    /// q:set of a.b.c, the root being the block's own (Some) or the world's variable (None). The root back when the
    /// block's own changed (a record it holds), for the machine to keep.
    fn assign_path(
        &mut self,
        name: &str,
        _root: Option<Value>,
        _value: Value,
        _line: u32,
    ) -> Result<Option<Value>, VmError> {
        rule(format!("q:set name=\"{name}\": there is no world here"))
    }
    /// What only the world does (q:move, q:emit, q:give...): its arguments as bytecode.py's effect() lays them out.
    fn effect(&mut self, name: &str, _args: Vec<Value>) -> Result<(), VmError> {
        rule(format!("<q:{name}> needs a world"))
    }
    /// The names a value has, for a suggestion (the Core's _names_of): a record's keys, else what Python's dir()
    /// says of it (a Python host knows; here, none); never those that start with _.
    fn names_of(&mut self, v: &Value) -> Result<Vec<String>, VmError> {
        Ok(match v {
            Value::Map(m) => m.keys().filter(|k| !k.starts_with('_')).cloned().collect(),
            Value::Entity(id) => self
                .keys(id)?
                .into_iter()
                .filter(|k| !k.starts_with('_'))
                .collect(),
            _ => Vec::new(),
        })
    }
    /// The names of the scope an expression runs in, for "variable x is not defined": the block's own here (a
    /// world's scope is a ChainMap: its host says).
    fn scope_names(&mut self, locals: &Locals) -> Vec<String> {
        locals
            .keys()
            .filter(|k| !k.starts_with('_'))
            .cloned()
            .collect()
    }
}

// -- the Core's suggestions (difflib's get_close_matches) ----------------------------------------------------------

/// difflib's find_longest_match, with no junk (b2j without the popular, as autojunk leaves it).
#[allow(clippy::too_many_arguments)]
fn longest_match(
    a: &[char],
    b: &[char],
    b2j: &HashMap<char, Vec<usize>>,
    alo: usize,
    ahi: usize,
    blo: usize,
    bhi: usize,
) -> (usize, usize, usize) {
    let (mut besti, mut bestj, mut bestsize) = (alo, blo, 0usize);
    let mut j2len: HashMap<usize, usize> = HashMap::new();
    for (i, c) in a.iter().enumerate().take(ahi).skip(alo) {
        let mut next: HashMap<usize, usize> = HashMap::new();
        if let Some(js) = b2j.get(c) {
            for &j in js {
                if j < blo {
                    continue;
                }
                if j >= bhi {
                    break;
                }
                let k = j
                    .checked_sub(1)
                    .and_then(|p| j2len.get(&p))
                    .copied()
                    .unwrap_or(0)
                    + 1;
                next.insert(j, k);
                if k > bestsize {
                    (besti, bestj, bestsize) = (i + 1 - k, j + 1 - k, k);
                }
            }
        }
        j2len = next;
    }
    while besti > alo && bestj > blo && a[besti - 1] == b[bestj - 1] {
        (besti, bestj, bestsize) = (besti - 1, bestj - 1, bestsize + 1);
    }
    while besti + bestsize < ahi
        && bestj + bestsize < bhi
        && a[besti + bestsize] == b[bestj + bestsize]
    {
        bestsize += 1;
    }
    (besti, bestj, bestsize)
}

/// SequenceMatcher(None, a, b).ratio().
fn ratio(a: &[char], b: &[char]) -> f64 {
    let total = a.len() + b.len();
    if total == 0 {
        return 1.0;
    }
    let mut b2j: HashMap<char, Vec<usize>> = HashMap::new();
    for (j, c) in b.iter().enumerate() {
        b2j.entry(*c).or_default().push(j);
    }
    if b.len() >= 200 {
        let most = b.len() / 100 + 1;
        b2j.retain(|_, js| js.len() <= most);
    }
    let mut matched = 0usize;
    let mut queue = vec![(0, a.len(), 0, b.len())];
    while let Some((alo, ahi, blo, bhi)) = queue.pop() {
        let (i, j, k) = longest_match(a, b, &b2j, alo, ahi, blo, bhi);
        if k > 0 {
            matched += k;
            if alo < i && blo < j {
                queue.push((alo, i, blo, j));
            }
            if i + k < ahi && j + k < bhi {
                queue.push((i + k, ahi, j + k, bhi));
            }
        }
    }
    2.0 * matched as f64 / total as f64
}

/// difflib.get_close_matches(word, names, n=3, cutoff=0.6).
fn close_matches(word: &str, names: &[String]) -> Vec<String> {
    let b: Vec<char> = word.chars().collect();
    let mut scored: Vec<(f64, &String)> = names
        .iter()
        .filter_map(|x| {
            let r = ratio(&x.chars().collect::<Vec<_>>(), &b);
            (r >= 0.6).then_some((r, x))
        })
        .collect();
    scored.sort_by(|p, q| {
        q.0.partial_cmp(&p.0)
            .unwrap_or(Ordering::Equal)
            .then_with(|| q.1.cmp(p.1))
    });
    scored.into_iter().take(3).map(|(_, x)| x.clone()).collect()
}

/// The Core's _suggest: `, did you mean 'x'?`, or what is there while it is short, or nothing.
fn suggest(wanted: &str, mut names: Vec<String>) -> String {
    if names.is_empty() {
        return String::new();
    }
    let close = close_matches(wanted, &names);
    if !close.is_empty() {
        let quoted: Vec<String> = close.iter().map(|c| str_repr(c)).collect();
        return format!(", did you mean {}?", quoted.join(" or "));
    }
    if names.len() <= 8 {
        names.sort();
        return format!(" (in scope: {})", names.join(", "));
    }
    String::new()
}

// -- Python's values ------------------------------------------------------------------------------------------------

pub fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Int(i) => *i != 0,
        Value::Big(_) => true,
        Value::Float(f) => *f != 0.0,
        Value::Str(s) => !s.is_empty(),
        Value::List(x) | Value::Tuple(x) => !x.is_empty(),
        Value::Map(m) => !m.is_empty(),
        Value::Json(_) | Value::Entity(_) => true,
    }
}

/// Python's type(v).__name__.
pub fn type_name_of(v: &Value) -> &'static str {
    type_name(v)
}

fn type_name(v: &Value) -> &'static str {
    match v {
        Value::Null => "NoneType",
        Value::Bool(_) => "bool",
        Value::Int(_) | Value::Big(_) => "int",
        Value::Float(_) => "float",
        Value::Str(_) | Value::Json(_) => "str",
        Value::List(_) => "list",
        Value::Tuple(_) => "tuple",
        Value::Map(_) | Value::Entity(_) => "dict",
    }
}

/// Python's whitespace, as str.strip() takes it.
fn is_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

fn py_strip(s: &str) -> &str {
    s.trim_matches(is_space)
}

/// Digits as Python's int() reads them: one underscore at most between two digits.
fn digits_ok(s: &str) -> bool {
    let b = s.as_bytes();
    !b.is_empty()
        && b[0].is_ascii_digit()
        && b[b.len() - 1].is_ascii_digit()
        && b.iter().all(|c| c.is_ascii_digit() || *c == b'_')
        && !s.contains("__")
}

/// Python's int(text), in base 10: None when it does not read as one.
pub fn parse_int(text: &str) -> Option<Value> {
    let t = py_strip(text);
    let (sign, body) = match t.as_bytes().first() {
        Some(b'+') => ("", &t[1..]),
        Some(b'-') => ("-", &t[1..]),
        _ => ("", t),
    };
    if !digits_ok(body) {
        return None;
    }
    let clean: String = body.chars().filter(|c| *c != '_').collect();
    let whole = format!("{sign}{clean}");
    Some(match whole.parse::<i64>() {
        Ok(i) => Value::Int(i),
        Err(_) => {
            let trimmed = clean.trim_start_matches('0');
            Value::Big(format!(
                "{sign}{}",
                if trimmed.is_empty() { "0" } else { trimmed }
            ))
        }
    })
}

/// Python's float(text): None when it does not read as one.
pub fn parse_float(text: &str) -> Option<f64> {
    let t = py_strip(text);
    let (neg, body) = match t.as_bytes().first() {
        Some(b'+') => (false, &t[1..]),
        Some(b'-') => (true, &t[1..]),
        _ => (false, t),
    };
    let lower = body.to_ascii_lowercase();
    let value = if lower == "inf" || lower == "infinity" {
        f64::INFINITY
    } else if lower == "nan" {
        f64::NAN
    } else {
        // digits, a point, an exponent; underscores only between digits
        let (mantissa, exponent) = match lower.find('e') {
            Some(i) => (&lower[..i], Some(&lower[i + 1..])),
            None => (&lower[..], None),
        };
        let (whole, fraction) = match mantissa.find('.') {
            Some(i) => (&mantissa[..i], Some(&mantissa[i + 1..])),
            None => (mantissa, None),
        };
        let part_ok = |p: &str| p.is_empty() || digits_ok(p);
        if !part_ok(whole)
            || !fraction.is_none_or(part_ok)
            || (whole.is_empty() && fraction.is_none_or(|f| f.is_empty()))
        {
            return None;
        }
        if let Some(e) = exponent {
            let digits = e.strip_prefix(['+', '-']).unwrap_or(e);
            if !digits_ok(digits) {
                return None;
            }
        }
        lower.replace('_', "").parse::<f64>().ok()?
    };
    Some(if neg { -value } else { value })
}

/// The Core's coerce_number: a text that reads as a number is that number.
pub fn coerce(v: &Value) -> Value {
    if let Value::Str(s) = v {
        if py_strip(s).is_empty() {
            return v.clone();
        }
        if let Some(i) = parse_int(s) {
            return i;
        }
        if let Some(f) = parse_float(s) {
            return Value::Float(f);
        }
    }
    v.clone()
}

fn numeric(v: &Value) -> bool {
    matches!(v, Value::Int(_) | Value::Big(_) | Value::Float(_))
}

fn big_refused<T>() -> Result<T, VmError> {
    err("a whole number past 64 bits: the engine's numbers are 64 bits (PLAN_WORLD_ENGINE.md)")
}

fn as_f64(v: &Value) -> Result<f64, VmError> {
    match v {
        Value::Int(i) => Ok(*i as f64),
        Value::Bool(b) => Ok(*b as i64 as f64),
        Value::Float(f) => Ok(*f),
        Value::Big(_) => big_refused(),
        _ => err(format!("a {} is not a number", type_name(v))),
    }
}

/// CPython's float divmod: (floor division, modulo), the modulo with the divisor's sign.
fn float_divmod(vx: f64, wx: f64) -> (f64, f64) {
    let mut m = vx % wx;
    let mut div = (vx - m) / wx;
    if m != 0.0 {
        if (wx < 0.0) != (m < 0.0) {
            m += wx;
            div -= 1.0;
        }
    } else {
        m = 0.0f64.copysign(wx);
    }
    let floordiv = if div != 0.0 {
        let f = div.floor();
        if div - f > 0.5 {
            f + 1.0
        } else {
            f
        }
    } else {
        0.0f64.copysign(vx / wx)
    };
    (floordiv, m)
}

fn int_bits(i: i64) -> u32 {
    64 - i.unsigned_abs().leading_zeros()
}

/// The Core's _guard_pow: a power of more than 4096 bits would not finish.
fn guard_pow(l: &Value, r: &Value) -> Result<(), VmError> {
    let too_large = || {
        err(format!(
            "{}**{} is too large to compute (over 4096 bits); this would hang the request",
            py_str(l),
            py_str(r)
        ))
    };
    match (l, r) {
        (Value::Int(a), Value::Int(b)) => {
            if *b < 0 || matches!(*a, -1..=1) {
                return Ok(());
            }
            if (*b as i128) * (int_bits(*a).max(1) as i128) > 4096 {
                return too_large();
            }
            Ok(())
        }
        _ => {
            let (a, b) = (as_f64(l)?, as_f64(r)?);
            if b < 0.0 || a == 0.0 || a == 1.0 || a == -1.0 {
                return Ok(());
            }
            let base = a.abs();
            if base <= 1.0 {
                return Ok(());
            }
            let bits = b * base.log2();
            if bits.is_nan() || bits > 4096.0 {
                return too_large();
            }
            Ok(())
        }
    }
}

const BIN_SYMBOLS: [&str; 7] = ["+", "-", "*", "/", "//", "%", "**"];

pub fn binop(op: u32, left: Value, right: Value) -> Result<Value, VmError> {
    let (cl, cr) = (coerce(&left), coerce(&right));
    if !(numeric(&cl) && numeric(&cr)) {
        if op == 0 {
            return match (left, right) {
                (Value::Str(a), Value::Str(b)) => Ok(Value::Str(a + &b)),
                (Value::List(mut a), Value::List(b)) => {
                    a.extend(b);
                    Ok(Value::List(a))
                }
                (l, r) => err(format!(
                    "'+' needs two numbers, two texts or two lists, got {} and {}",
                    py_repr(&l),
                    py_repr(&r)
                )),
            };
        }
        return err(format!(
            "'{}' needs two numbers, got {} and {}",
            BIN_SYMBOLS[op as usize],
            py_repr(&left),
            py_repr(&right)
        ));
    }
    if op == 6 {
        guard_pow(&cl, &cr)?;
    }
    if matches!(cl, Value::Big(_)) || matches!(cr, Value::Big(_)) {
        return big_refused();
    }
    let overflow = || big_refused::<Value>();
    match (&cl, &cr) {
        (Value::Int(a), Value::Int(b)) => {
            let (a, b) = (*a, *b);
            match op {
                0 => a.checked_add(b).map(Value::Int).map_or_else(overflow, Ok),
                1 => a.checked_sub(b).map(Value::Int).map_or_else(overflow, Ok),
                2 => a.checked_mul(b).map(Value::Int).map_or_else(overflow, Ok),
                3 => {
                    if b == 0 {
                        return err("division by zero");
                    }
                    Ok(Value::Float(a as f64 / b as f64))
                }
                4 | 5 => {
                    if b == 0 {
                        return err("division by zero");
                    }
                    if a == i64::MIN && b == -1 {
                        return overflow();
                    }
                    let (mut q, mut r) = (a / b, a % b);
                    if r != 0 && ((r < 0) != (b < 0)) {
                        q -= 1;
                        r += b;
                    }
                    Ok(Value::Int(if op == 4 { q } else { r }))
                }
                _ => {
                    if b < 0 {
                        if a == 0 {
                            return err("division by zero");
                        }
                        return float_pow(a as f64, b as f64);
                    }
                    let e = u32::try_from(b)
                        .map_err(|_| VmError::new(ErrorKind::Expression, "too large"))?;
                    a.checked_pow(e).map(Value::Int).map_or_else(overflow, Ok)
                }
            }
        }
        _ => {
            let (a, b) = (as_f64(&cl)?, as_f64(&cr)?);
            match op {
                0 => Ok(Value::Float(a + b)),
                1 => Ok(Value::Float(a - b)),
                2 => Ok(Value::Float(a * b)),
                3 => {
                    if b == 0.0 {
                        return err("division by zero");
                    }
                    Ok(Value::Float(a / b))
                }
                4 | 5 => {
                    if b == 0.0 {
                        return err("division by zero");
                    }
                    let (q, m) = float_divmod(a, b);
                    Ok(Value::Float(if op == 4 { q } else { m }))
                }
                _ => float_pow(a, b),
            }
        }
    }
}

fn float_pow(a: f64, b: f64) -> Result<Value, VmError> {
    if a == 0.0 && b < 0.0 {
        return err("division by zero");
    }
    if a < 0.0 && b.is_finite() && b.fract() != 0.0 {
        return err("a negative number to a fractional power is a complex number, not a world's");
    }
    let r = a.powf(b);
    if r.is_infinite() && a.is_finite() && b.is_finite() {
        return err("the result is too large to represent: (34, 'Numerical result out of range')");
    }
    Ok(Value::Float(r))
}

pub fn unary(op: u32, v: Value) -> Result<Value, VmError> {
    if op == 2 {
        return Ok(Value::Bool(!truthy(&v)));
    }
    let v = coerce(&v);
    match (op, v) {
        (0, Value::Int(i)) => i.checked_neg().map(Value::Int).map_or_else(big_refused, Ok),
        (0, Value::Bool(b)) => Ok(Value::Int(-(b as i64))),
        (0, Value::Float(f)) => Ok(Value::Float(-f)),
        (1, Value::Int(i)) => Ok(Value::Int(i)),
        (1, Value::Bool(b)) => Ok(Value::Int(b as i64)),
        (1, Value::Float(f)) => Ok(Value::Float(f)),
        (_, Value::Big(_)) => big_refused(),
        // the Core does not catch it: a TypeError, as Python's
        (_, other) => raise(
            Raise::Type,
            format!(
                "bad operand type for unary {}: '{}'",
                if op == 0 { "-" } else { "+" },
                type_name(&other)
            ),
        ),
    }
}

/// 2 ** 63, the first float past an i64.
const TWO_63: f64 = 9_223_372_036_854_775_808.0;

/// An int against a float, exactly (Python compares them so).
fn cmp_int_float(i: i64, f: f64) -> Option<Ordering> {
    if f.is_nan() {
        return None;
    }
    if f.is_infinite() {
        return Some(if f > 0.0 {
            Ordering::Less
        } else {
            Ordering::Greater
        });
    }
    let t = f.trunc();
    if t >= TWO_63 {
        return Some(Ordering::Less);
    }
    if t < -TWO_63 {
        return Some(Ordering::Greater);
    }
    match i.cmp(&(t as i64)) {
        Ordering::Equal => {
            let frac = f - t;
            Some(if frac > 0.0 {
                Ordering::Less
            } else if frac < 0.0 {
                Ordering::Greater
            } else {
                Ordering::Equal
            })
        }
        other => Some(other),
    }
}

/// Python's ordering of two values: None when they are not ordered (a NaN), Err when they cannot be (a TypeError).
/// Python's ordering of two values; what it cannot order is a TypeError that names the operator (`sym`).
fn py_cmp(a: &Value, b: &Value, sym: &str) -> Result<Option<Ordering>, VmError> {
    use Value::*;
    let whole = |v: &Value| match v {
        Int(i) => Some(*i),
        Bool(x) => Some(*x as i64),
        _ => None,
    };
    match (a, b) {
        (Int(_) | Bool(_), Int(_) | Bool(_)) => Ok(Some(whole(a).unwrap().cmp(&whole(b).unwrap()))),
        (Float(x), Float(y)) => Ok(x.partial_cmp(y)),
        (Int(_) | Bool(_), Float(y)) => Ok(cmp_int_float(whole(a).unwrap(), *y)),
        (Float(x), Int(_) | Bool(_)) => {
            Ok(cmp_int_float(whole(b).unwrap(), *x).map(Ordering::reverse))
        }
        (Big(_), _) | (_, Big(_)) if numeric(a) || numeric(b) => big_refused(),
        (Str(x), Str(y)) => Ok(Some(x.cmp(y))),
        (List(x), List(y)) | (Tuple(x), Tuple(y)) => {
            for (p, q) in x.iter().zip(y) {
                if !py_eq(p, q) {
                    return py_cmp(p, q, sym);
                }
            }
            Ok(Some(x.len().cmp(&y.len())))
        }
        _ => err(format!(
            "cannot compare: '{sym}' not supported between instances of '{}' and '{}'",
            type_name(a),
            type_name(b)
        )),
    }
}

fn py_lt(a: &Value, b: &Value) -> Result<bool, VmError> {
    Ok(py_cmp(a, b, "<")? == Some(Ordering::Less))
}

/// The Core's `==`: a numeric text equals its number.
pub fn equal(a: &Value, b: &Value) -> bool {
    let (ca, cb) = (coerce(a), coerce(b));
    if numeric(&ca) && numeric(&cb) {
        py_eq(&ca, &cb)
    } else {
        py_eq(a, b)
    }
}

fn contains(host: &mut dyn Host, container: &Value, item: &Value) -> Result<bool, VmError> {
    match container {
        Value::Str(s) => Ok(match item {
            Value::Str(t) => s.contains(t.as_str()),
            other => s.contains(py_str(other).as_str()),
        }),
        Value::List(x) | Value::Tuple(x) => Ok(x.iter().any(|e| equal(item, e))),
        Value::Map(m) => Ok(m.keys().any(|k| equal(item, &Value::Str(k.clone())))),
        Value::Entity(id) => Ok(host
            .keys(id)?
            .into_iter()
            .any(|k| equal(item, &Value::Str(k)))),
        other => err(format!(
            "cannot compare: 'in' needs a list, an object or a text, not {}",
            type_name(other)
        )),
    }
}

pub fn compare(host: &mut dyn Host, op: u32, left: &Value, right: &Value) -> Result<bool, VmError> {
    if op >= 6 {
        let inside = contains(host, right, left)?;
        return Ok(if op == 6 { inside } else { !inside });
    }
    let (cl, cr) = (coerce(left), coerce(right));
    let (l, r) = if numeric(&cl) && numeric(&cr) {
        (&cl, &cr)
    } else {
        (left, right)
    };
    Ok(match op {
        0 => py_eq(l, r),
        1 => !py_eq(l, r),
        _ => {
            let ord = py_cmp(l, r, ["<", "<=", ">", ">="][op as usize - 2])?;
            match op {
                2 => ord == Some(Ordering::Less),
                3 => matches!(ord, Some(Ordering::Less | Ordering::Equal)),
                4 => ord == Some(Ordering::Greater),
                _ => matches!(ord, Some(Ordering::Greater | Ordering::Equal)),
            }
        }
    })
}

// -- Python's str() and repr() -------------------------------------------------------------------------------------

fn float_text(f: f64) -> String {
    if f.is_nan() {
        return "nan".into();
    }
    if f.is_infinite() {
        return if f > 0.0 { "inf".into() } else { "-inf".into() };
    }
    let mut s = String::new();
    write_float(f, &mut s);
    s
}

fn printable(c: char) -> bool {
    let n = c as u32;
    if n < 0x20 || (0x7f..0xa0).contains(&n) {
        return false;
    }
    !matches!(n,
        0xad | 0x1680 | 0x2000..=0x200f | 0x2028..=0x202f | 0x205f..=0x2064 | 0x3000 | 0xfeff | 0xe000..=0xf8ff
        | 0xfff9..=0xfffb | 0xf0000..=0x10ffff)
}

pub fn str_repr(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::new();
    out.push(quote);
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if printable(c) => out.push(c),
            c if (c as u32) < 0x100 => out.push_str(&format!("\\x{:02x}", c as u32)),
            c if (c as u32) < 0x10000 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push_str(&format!("\\U{:08x}", c as u32)),
        }
    }
    out.push(quote);
    out
}

pub fn py_repr(v: &Value) -> String {
    match v {
        Value::Str(s) => str_repr(s),
        Value::Json(j) => j.clone(),
        Value::List(x) => format!("[{}]", x.iter().map(py_repr).collect::<Vec<_>>().join(", ")),
        Value::Tuple(x) if x.len() == 1 => format!("({},)", py_repr(&x[0])),
        Value::Tuple(x) => format!("({})", x.iter().map(py_repr).collect::<Vec<_>>().join(", ")),
        Value::Map(m) => format!(
            "{{{}}}",
            m.iter()
                .map(|(k, v)| format!("{}: {}", str_repr(k), py_repr(v)))
                .collect::<Vec<_>>()
                .join(", ")
        ),
        other => py_str(other),
    }
}

/// Python's str() of a value.
pub fn py_str(v: &Value) -> String {
    match v {
        Value::Null => "None".into(),
        Value::Bool(true) => "True".into(),
        Value::Bool(false) => "False".into(),
        Value::Int(i) => i.to_string(),
        Value::Big(d) => d.clone(),
        Value::Float(f) => float_text(*f),
        Value::Str(s) => s.clone(),
        Value::Entity(id) => format!("{{'id': {}, ...}}", str_repr(id)),
        other => py_repr(other),
    }
}

// -- the machine's stdlib (quantum/core/expression_stdlib.py) ------------------------------------------------------

fn failed<T>(name: &str, why: impl std::fmt::Display) -> Result<T, VmError> {
    err(format!("{name}() failed: {why}"))
}

/// What iterating a value gives (Python's list(v)): a list's items, a text's characters, a record's keys.
fn items_of(host: &mut dyn Host, name: &str, v: &Value) -> Result<Vec<Value>, VmError> {
    Ok(match v {
        Value::List(x) | Value::Tuple(x) => x.clone(),
        Value::Str(s) => s.chars().map(|c| Value::Str(c.to_string())).collect(),
        Value::Map(m) => m.keys().map(|k| Value::Str(k.clone())).collect(),
        Value::Entity(id) => host.keys(id)?.into_iter().map(Value::Str).collect(),
        other => {
            return failed(
                name,
                format!("'{}' object is not iterable", type_name(other)),
            )
        }
    })
}

fn to_int(name: &str, v: &Value) -> Result<Value, VmError> {
    match v {
        Value::Int(_) | Value::Big(_) => Ok(v.clone()),
        Value::Bool(b) => Ok(Value::Int(*b as i64)),
        Value::Float(f) => {
            if !f.is_finite() {
                return failed(name, "cannot convert float infinity or NaN to integer");
            }
            let t = f.trunc();
            if t.abs() >= TWO_63 {
                return big_refused();
            }
            Ok(Value::Int(t as i64))
        }
        Value::Str(s) => parse_int(s).map_or_else(
            || {
                failed(
                    name,
                    format!("invalid literal for int() with base 10: {}", str_repr(s)),
                )
            },
            Ok,
        ),
        other => failed(
            name,
            format!(
                "int() argument must be a string, a bytes-like object or a real number, not '{}'",
                type_name(other)
            ),
        ),
    }
}

fn to_float(name: &str, v: &Value) -> Result<f64, VmError> {
    match v {
        Value::Str(s) => parse_float(s).map_or_else(
            || {
                failed(
                    name,
                    format!("could not convert string to float: {}", str_repr(s)),
                )
            },
            Ok,
        ),
        Value::Int(_) | Value::Bool(_) | Value::Float(_) => as_f64(v),
        Value::Big(_) => big_refused(),
        other => failed(
            name,
            format!(
                "float() argument must be a string or a real number, not '{}'",
                type_name(other)
            ),
        ),
    }
}

fn whole_index(v: &Value) -> Option<i64> {
    match v {
        Value::Int(i) => Some(*i),
        Value::Bool(b) => Some(*b as i64),
        _ => None,
    }
}

/// The Core's round: Decimal(str(v)).quantize(10 ** -digits, ROUND_HALF_UP), an int for digits <= 0.
fn round(v: &Value, digits: i64) -> Result<Value, VmError> {
    let text = py_str(v);
    let t = py_strip(&text).replace('_', "");
    let (neg, body) = match t.as_bytes().first() {
        Some(b'-') => (true, &t[1..]),
        Some(b'+') => (false, &t[1..]),
        _ => (false, &t[..]),
    };
    let (mantissa, exp) = match body.find(['e', 'E']) {
        Some(i) => (
            &body[..i],
            body[i + 1..].parse::<i64>().map_err(|_| {
                VmError::new(
                    ErrorKind::Expression,
                    "round() failed: [<class 'decimal.ConversionSyntax'>]",
                )
            })?,
        ),
        None => (body, 0),
    };
    let (whole, fraction) = mantissa.split_once('.').unwrap_or((mantissa, ""));
    if (whole.is_empty() && fraction.is_empty())
        || !whole
            .bytes()
            .chain(fraction.bytes())
            .all(|c| c.is_ascii_digit())
    {
        // Decimal(str(v)): an infinity cannot be quantized, a NaN stays one, the rest does not read
        let word = body.to_ascii_lowercase();
        if word == "inf" || word == "infinity" || word.starts_with("snan") {
            return failed("round", "[<class 'decimal.InvalidOperation'>]");
        }
        if word.starts_with("nan") && word[3..].bytes().all(|c| c.is_ascii_digit()) {
            return if digits <= 0 {
                failed("round", "cannot convert NaN to integer")
            } else {
                Ok(Value::Float(f64::NAN))
            };
        }
        return failed("round", "[<class 'decimal.ConversionSyntax'>]");
    }
    // the number is digits * 10 ** e
    let mut digits_all: Vec<u8> = whole
        .bytes()
        .chain(fraction.bytes())
        .map(|c| c - b'0')
        .collect();
    let e = exp - fraction.len() as i64;
    let keep = -digits; // the result's exponent
    if e < keep {
        let drop = (keep - e) as usize;
        let n = digits_all.len();
        let (kept, gone): (Vec<u8>, Vec<u8>) = if drop >= n {
            (vec![], {
                let mut g = vec![0; drop - n];
                g.extend(&digits_all);
                g
            })
        } else {
            (
                digits_all[..n - drop].to_vec(),
                digits_all[n - drop..].to_vec(),
            )
        };
        digits_all = if kept.is_empty() { vec![0] } else { kept };
        if gone.first().is_some_and(|d| *d >= 5) {
            let mut i = digits_all.len();
            loop {
                if i == 0 {
                    digits_all.insert(0, 1);
                    break;
                }
                i -= 1;
                if digits_all[i] == 9 {
                    digits_all[i] = 0;
                } else {
                    digits_all[i] += 1;
                    break;
                }
            }
        }
    } else {
        digits_all.extend(std::iter::repeat_n(0, (e - keep) as usize));
    }
    while digits_all.len() > 1 && digits_all[0] == 0 {
        digits_all.remove(0);
    }
    if digits_all.len() > 28 {
        return failed("round", "[<class 'decimal.InvalidOperation'>]");
    }
    let coefficient: String = digits_all.iter().map(|d| (b'0' + d) as char).collect();
    if digits <= 0 {
        let mut text = coefficient;
        text.extend(std::iter::repeat_n('0', (-digits) as usize));
        let zero = text.bytes().all(|c| c == b'0');
        let text = if neg && !zero {
            format!("-{text}")
        } else {
            text
        };
        return Ok(parse_int(&text).unwrap_or(Value::Big(text)));
    }
    let text = format!("{}{}e-{}", if neg { "-" } else { "" }, coefficient, digits);
    Ok(Value::Float(text.parse::<f64>().unwrap_or(f64::NAN)))
}

fn min_max(
    host: &mut dyn Host,
    name: &str,
    args: Vec<Value>,
    kwargs: Vec<(String, Value)>,
) -> Result<Value, VmError> {
    let mut default = None;
    for (k, v) in kwargs {
        if k == "default" {
            default = Some(v);
        } else {
            return failed(
                name,
                format!("'{k}' is an invalid keyword argument for {name}()"),
            );
        }
    }
    let items = match args.len() {
        0 => return failed(name, format!("{name} expected at least 1 argument, got 0")),
        1 => items_of(host, name, &args[0])?,
        _ => {
            if default.is_some() {
                return failed(
                    name,
                    format!(
                        "Cannot specify a default for {name}() with multiple positional arguments"
                    ),
                );
            }
            args
        }
    };
    let mut best: Option<Value> = None;
    for item in items {
        best = Some(match best {
            None => item,
            Some(b) => {
                // Python's min asks item < best, max item > best
                let better = if name == "min" {
                    py_cmp(&item, &b, "<").map(|o| o == Some(Ordering::Less))
                } else {
                    py_cmp(&item, &b, ">").map(|o| o == Some(Ordering::Greater))
                };
                if better.map_err(|e| {
                    VmError::new(
                        ErrorKind::Expression,
                        format!(
                            "{name}() failed: {}",
                            e.message.trim_start_matches("cannot compare: ")
                        ),
                    )
                })? {
                    item
                } else {
                    b
                }
            }
        });
    }
    match (best, default) {
        (Some(b), _) => Ok(b),
        (None, Some(d)) => Ok(d),
        (None, None) => failed(name, format!("{name}() iterable argument is empty")),
    }
}

fn sort(host: &mut dyn Host, args: &[Value], kwargs: &[(String, Value)]) -> Result<Value, VmError> {
    let mut reverse = args.get(1).cloned();
    for (k, v) in kwargs {
        if k == "reverse" {
            reverse = Some(v.clone());
        } else {
            return failed(
                "sort",
                format!("_sort() got an unexpected keyword argument '{k}'"),
            );
        }
    }
    if args.is_empty() || args.len() > 2 {
        return failed("sort", "_sort() takes from 1 to 2 positional arguments");
    }
    let reverse = match reverse {
        None => false,
        Some(Value::Bool(b)) => b,
        Some(Value::Int(i)) => i != 0,
        Some(other) => {
            return failed(
                "sort",
                format!(
                    "'{}' object cannot be interpreted as an integer",
                    type_name(&other)
                ),
            )
        }
    };
    let mut items = items_of(host, "sort", &args[0])?;
    // list.sort(reverse=True) sorts the reversed list and reverses it back (so equal ones keep their order)
    if reverse {
        items.reverse();
    }
    py_sort(&mut items).map_err(|e| {
        VmError::new(
            ErrorKind::Expression,
            format!(
                "sort() failed: {}",
                e.message.trim_start_matches("cannot compare: ")
            ),
        )
    })?;
    if reverse {
        items.reverse();
    }
    Ok(Value::List(items))
}

/// Python 3.13's list.sort() finds its first run as 3.12's does not (gh-116554): a sort that fails says the pair it
/// compared first, so the machine compares as the Python it serves does (python.rs sets it).
pub static SORTS_AS_313: AtomicBool = AtomicBool::new(false);

/// CPython's list.sort(), comparison by comparison, for a list of fewer than 64 (one run, then binary insertion):
/// a value that cannot be ordered fails on the pair Python's fails on. A longer list is merge sorted (the same
/// order; a failure may name another pair).
fn py_sort(a: &mut [Value]) -> Result<(), VmError> {
    let n = a.len();
    if n < 2 {
        return Ok(());
    }
    if n >= 64 {
        let mut problem = None;
        a.sort_by(|x, y| match (py_lt(y, x), problem.is_some()) {
            (_, true) => Ordering::Equal,
            (Ok(true), _) => Ordering::Greater,
            (Ok(false), _) => match py_lt(x, y) {
                Ok(true) => Ordering::Less,
                Ok(false) => Ordering::Equal,
                Err(e) => {
                    problem = Some(e);
                    Ordering::Equal
                }
            },
            (Err(e), _) => {
                problem = Some(e);
                Ordering::Equal
            }
        });
        return problem.map_or(Ok(()), Err);
    }
    let run = if SORTS_AS_313.load(Relaxed) {
        count_run_313(a)?
    } else {
        count_run_312(a)?
    };
    // binary insertion of the rest
    for ok in run..n {
        let (mut lo, mut hi) = (0, ok);
        while lo < hi {
            let mid = (lo + hi) >> 1;
            if py_lt(&a[ok], &a[mid])? {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        a[lo..=ok].rotate_right(1);
    }
    Ok(())
}

/// listobject.c's count_run, 3.12: the first run, ascending or strictly descending (reversed in place).
fn count_run_312(a: &mut [Value]) -> Result<usize, VmError> {
    let mut n = 2;
    if py_lt(&a[1], &a[0])? {
        while n < a.len() && py_lt(&a[n], &a[n - 1])? {
            n += 1;
        }
        a[..n].reverse();
    } else {
        while n < a.len() && !py_lt(&a[n], &a[n - 1])? {
            n += 1;
        }
    }
    Ok(n)
}

/// listobject.c's count_run, 3.13: a descending run may hold equal ones (each such stretch reversed on the way).
fn count_run_313(a: &mut [Value]) -> Result<usize, VmError> {
    let len = a.len();
    let mut n = 1;
    while n < len && !py_lt(&a[n], &a[n - 1])? {
        n += 1;
    }
    if n == len {
        return Ok(n);
    }
    if n > 1 {
        if py_lt(&a[0], &a[n - 1])? {
            return Ok(n);
        }
        a[..n].reverse();
    }
    n += 1;
    let mut neq = 0;
    let reverse_last = |a: &mut [Value], n: usize, neq: &mut usize| {
        if *neq > 0 {
            *neq += 1;
            a[n - *neq..n].reverse();
            *neq = 0;
        }
    };
    while n < len {
        if py_lt(&a[n], &a[n - 1])? {
            reverse_last(a, n, &mut neq);
        } else if py_lt(&a[n - 1], &a[n])? {
            break;
        } else {
            neq += 1;
        }
        n += 1;
    }
    reverse_last(a, n, &mut neq);
    a[..n].reverse();
    Ok(n)
}

fn text_arg<'a>(name: &str, v: Option<&'a Value>, what: &str) -> Result<&'a str, VmError> {
    match v {
        Some(Value::Str(s)) => Ok(s),
        // Argument Clinic's wording: None by name, the rest by type
        Some(Value::Null) => failed(name, format!("{what} must be str, not None")),
        Some(other) => failed(
            name,
            format!("{what} must be str, not {}", type_name(other)),
        ),
        None => failed(name, "missing argument"),
    }
}

/// A function of the Core's stdlib written in Python (expression_stdlib.py): its name there, its parameters, how
/// many of them have no default.
fn signature(name: &str) -> Option<(&'static str, &'static [&'static str], usize)> {
    Some(match name {
        "len" => ("_len", &["v"], 1),
        "first" => ("_first", &["v"], 1),
        "last" => ("_last", &["v"], 1),
        "join" => ("_join", &["v", "sep"], 1),
        "sort" => ("_sort", &["v", "reverse"], 1),
        "get" => ("_get", &["container", "key", "default"], 2),
        "round" => ("_round", &["v", "digits"], 1),
        "ceil" => ("_ceil", &["v"], 1),
        "floor" => ("_floor", &["v"], 1),
        "upper" => ("_upper", &["v"], 1),
        "lower" => ("_lower", &["v"], 1),
        "trim" => ("_trim", &["v"], 1),
        "replace" => ("_replace", &["v", "old", "new"], 3),
        "split" => ("_split", &["v", "sep"], 1),
        "contains" => ("_contains", &["v", "needle"], 2),
        _ => return None,
    })
}

/// Python's binding of a call's arguments to a function's parameters, with its TypeErrors word for word: the
/// arguments in order (those not given and with a default left off the end).
pub fn bind(
    (py, params, required): (&str, &[&str], usize),
    args: Vec<Value>,
    kwargs: Vec<(String, Value)>,
) -> Result<Vec<Value>, String> {
    let given = args.len();
    let mut slots: Vec<Option<Value>> = vec![None; params.len()];
    for (slot, a) in slots.iter_mut().zip(args) {
        *slot = Some(a);
    }
    for (k, v) in kwargs {
        match params.iter().position(|p| *p == k) {
            None => return Err(format!("{py}() got an unexpected keyword argument '{k}'")),
            Some(i) if slots[i].is_some() => {
                return Err(format!("{py}() got multiple values for argument '{k}'"))
            }
            Some(i) => slots[i] = Some(v),
        }
    }
    if given > params.len() {
        let takes = if required < params.len() {
            format!("from {required} to {} positional arguments", params.len())
        } else {
            format!(
                "{} positional argument{}",
                params.len(),
                if params.len() == 1 { "" } else { "s" }
            )
        };
        let was = if given == 1 { "was" } else { "were" };
        return Err(format!("{py}() takes {takes} but {given} {was} given"));
    }
    let missing: Vec<String> = (given..required)
        .filter(|i| slots[*i].is_none())
        .map(|i| str_repr(params[i]))
        .collect();
    if !missing.is_empty() {
        let names = match missing.len() {
            1 => missing[0].clone(),
            2 => format!("{} and {}", missing[0], missing[1]),
            n => format!("{}, and {}", missing[..n - 1].join(", "), missing[n - 1]),
        };
        return Err(format!(
            "{py}() missing {} required positional argument{}: {names}",
            missing.len(),
            if missing.len() == 1 { "" } else { "s" }
        ));
    }
    Ok(slots.into_iter().map_while(|s| s).collect())
}

pub fn native(
    host: &mut dyn Host,
    name: &str,
    args: Vec<Value>,
    kwargs: Vec<(String, Value)>,
) -> Result<Value, VmError> {
    let (args, kwargs) = match signature(name) {
        Some(sig) => match bind(sig, args, kwargs) {
            Ok(args) => (args, Vec::new()),
            Err(why) => return failed(name, why),
        },
        None => (args, kwargs),
    };
    // a builtin of one argument (abs, float, math.sqrt), as Python says it is not called so
    let one = |args: &Vec<Value>| -> Result<(), VmError> {
        let called = if name == "sqrt" { "math.sqrt" } else { name };
        if !kwargs.is_empty() {
            return failed(name, format!("{called}() takes no keyword arguments"));
        }
        if args.len() != 1 {
            if name == "float" {
                return failed(
                    name,
                    format!("float expected at most 1 argument, got {}", args.len()),
                );
            }
            return failed(
                name,
                format!(
                    "{called}() takes exactly one argument ({} given)",
                    args.len()
                ),
            );
        }
        Ok(())
    };
    match name {
        "len" => {
            one(&args)?;
            Ok(Value::Int(match &args[0] {
                Value::Str(s) => s.chars().count() as i64,
                Value::List(x) | Value::Tuple(x) => x.len() as i64,
                Value::Map(m) => m.len() as i64,
                Value::Entity(id) => host.keys(id)?.len() as i64,
                _ => 0,
            }))
        }
        "first" | "last" => {
            one(&args)?;
            let items = items_of(host, name, &args[0])?;
            Ok((if name == "first" {
                items.first()
            } else {
                items.last()
            })
            .cloned()
            .unwrap_or(Value::Null))
        }
        "join" => {
            if args.is_empty() || args.len() > 2 {
                return failed(name, "_join() takes from 1 to 2 positional arguments");
            }
            let sep = match args.get(1) {
                None => ", ".to_string(),
                Some(Value::Str(s)) => s.clone(),
                Some(other) => {
                    return failed(
                        name,
                        format!("'{}' object has no attribute 'join'", type_name(other)),
                    )
                }
            };
            let items = items_of(host, name, &args[0])?;
            Ok(Value::Str(
                items.iter().map(py_str).collect::<Vec<_>>().join(&sep),
            ))
        }
        "sort" => sort(host, &args, &kwargs),
        "get" => {
            if args.len() < 2 || args.len() > 3 {
                return failed(name, "_get() takes from 2 to 3 positional arguments");
            }
            let default = args.get(2).cloned().unwrap_or(Value::Null);
            if matches!(args[0], Value::Map(_) | Value::Entity(_)) && !hashable(&args[1]) {
                return failed(
                    name,
                    format!("unhashable type: '{}'", unhashable_in(&args[1])),
                );
            }
            match (&args[0], &args[1]) {
                (Value::Map(m), Value::Str(k)) => Ok(m.get(k).cloned().unwrap_or(default)),
                (Value::Map(_), _) => Ok(default),
                (Value::Entity(id), Value::Str(k)) => Ok(host.field(id, k)?.unwrap_or(default)),
                (Value::Entity(_), _) => Ok(default),
                (Value::List(x) | Value::Tuple(x), Value::Int(i)) => {
                    let n = x.len() as i64;
                    Ok(if -n <= *i && *i < n {
                        x[(if *i < 0 { i + n } else { *i }) as usize].clone()
                    } else {
                        default
                    })
                }
                (Value::Str(s), Value::Int(i)) => {
                    let chars: Vec<char> = s.chars().collect();
                    let n = chars.len() as i64;
                    Ok(if -n <= *i && *i < n {
                        Value::Str(chars[(if *i < 0 { i + n } else { *i }) as usize].to_string())
                    } else {
                        default
                    })
                }
                (Value::Null, _) => Ok(default),
                (c, _) => failed(
                    name,
                    format!(
                        "get() reads a key of an object or an index of a list, not of {}",
                        type_name(c)
                    ),
                ),
            }
        }
        "round" => {
            if args.is_empty() || args.len() > 2 {
                return failed(name, "_round() takes from 1 to 2 positional arguments");
            }
            let digits = match args.get(1) {
                None => 0,
                Some(d) => match to_int(name, d)? {
                    Value::Int(i) => i,
                    _ => return big_refused(),
                },
            };
            if matches!(
                args[0],
                Value::Null
                    | Value::Bool(_)
                    | Value::List(_)
                    | Value::Tuple(_)
                    | Value::Map(_)
                    | Value::Entity(_)
            ) {
                return failed(name, "[<class 'decimal.ConversionSyntax'>]");
            }
            round(&args[0], digits)
        }
        "ceil" | "floor" => {
            one(&args)?;
            let f = to_float(name, &args[0])?;
            if f.is_nan() {
                return failed(name, "cannot convert float NaN to integer");
            }
            if f.is_infinite() {
                return failed(name, "cannot convert float infinity to integer");
            }
            let r = if name == "ceil" { f.ceil() } else { f.floor() };
            if r.abs() >= TWO_63 {
                return big_refused();
            }
            Ok(Value::Int(r as i64))
        }
        "abs" => {
            one(&args)?;
            match &args[0] {
                Value::Int(i) => i.checked_abs().map(Value::Int).map_or_else(big_refused, Ok),
                Value::Bool(b) => Ok(Value::Int(*b as i64)),
                Value::Float(f) => Ok(Value::Float(f.abs())),
                Value::Big(d) => Ok(Value::Big(d.trim_start_matches('-').to_string())),
                other => failed(
                    name,
                    format!("bad operand type for abs(): '{}'", type_name(other)),
                ),
            }
        }
        "min" | "max" => min_max(host, name, args, kwargs),
        "int" => {
            if args.is_empty() {
                return Ok(Value::Int(0));
            }
            if args.len() > 1 || !kwargs.is_empty() {
                return failed(name, "int() in a world takes one argument (base 10)");
            }
            to_int(name, &args[0])
        }
        "float" => {
            if args.is_empty() {
                return Ok(Value::Float(0.0));
            }
            one(&args)?;
            to_float(name, &args[0]).map(Value::Float)
        }
        "str" => {
            if args.is_empty() {
                return Ok(Value::Str(String::new()));
            }
            one(&args)?;
            Ok(Value::Str(py_str(&args[0])))
        }
        "upper" | "lower" | "trim" => {
            one(&args)?;
            let s = py_str(&args[0]);
            Ok(Value::Str(match name {
                "upper" => s.to_uppercase(),
                "lower" => s.to_lowercase(),
                _ => py_strip(&s).to_string(),
            }))
        }
        "replace" => {
            if args.len() != 3 || !kwargs.is_empty() {
                return failed(name, "_replace() takes 3 positional arguments");
            }
            let old = text_arg(name, args.get(1), "replace() argument 1")?;
            let new = text_arg(name, args.get(2), "replace() argument 2")?;
            Ok(Value::Str(py_str(&args[0]).replace(old, new)))
        }
        "split" => {
            if args.is_empty() || args.len() > 2 || !kwargs.is_empty() {
                return failed(name, "_split() takes from 1 to 2 positional arguments");
            }
            let s = py_str(&args[0]);
            match args.get(1) {
                None => Ok(Value::List(
                    s.split(',').map(|p| Value::Str(p.into())).collect(),
                )),
                Some(Value::Null) => Ok(Value::List(
                    s.split(is_space)
                        .filter(|p| !p.is_empty())
                        .map(|p| Value::Str(p.into()))
                        .collect(),
                )),
                Some(Value::Str(sep)) if sep.is_empty() => failed(name, "empty separator"),
                Some(Value::Str(sep)) => Ok(Value::List(
                    s.split(sep.as_str())
                        .map(|p| Value::Str(p.into()))
                        .collect(),
                )),
                Some(other) => failed(
                    name,
                    format!("must be str or None, not {}", type_name(other)),
                ),
            }
        }
        "contains" => {
            if args.len() != 2 || !kwargs.is_empty() {
                return failed(name, "_contains() takes 2 positional arguments");
            }
            Ok(Value::Bool(
                py_str(&args[0]).contains(py_str(&args[1]).as_str()),
            ))
        }
        "sqrt" => {
            one(&args)?;
            let f = match &args[0] {
                Value::Int(_) | Value::Bool(_) | Value::Float(_) => as_f64(&args[0])?,
                Value::Big(_) => return big_refused(),
                other => {
                    return failed(
                        name,
                        format!("must be real number, not {}", type_name(other)),
                    )
                }
            };
            if f < 0.0 {
                return failed(name, "math domain error");
            }
            Ok(Value::Float(f.sqrt()))
        }
        _ => err(format!("function {} is not defined", str_repr(name))),
    }
}

// -- reading -------------------------------------------------------------------------------------------------------

const INT_DATA: [&str; 4] = ["real", "imag", "numerator", "denominator"];

fn attribute(host: &mut dyn Host, target: &Value, attr: &str) -> Result<Value, VmError> {
    let found = match target {
        Value::Map(m) => m.get(attr).cloned(),
        Value::Entity(id) => host.field(id, attr)?,
        _ => return data(host, target, attr),
    };
    match found {
        Some(v) => Ok(v),
        None => {
            let names = host.names_of(target)?;
            undefined(format!(
                "key {} not found{}",
                str_repr(attr),
                suggest(attr, names)
            ))
        }
    }
}

/// An attribute of what is not a record: a length, a number's data; a method is refused, as the rest.
fn data(host: &mut dyn Host, target: &Value, attr: &str) -> Result<Value, VmError> {
    match target {
        Value::List(x) | Value::Tuple(x) if attr == "length" => {
            return Ok(Value::Int(x.len() as i64))
        }
        Value::Str(s) if attr == "length" => return Ok(Value::Int(s.chars().count() as i64)),
        Value::Int(_) | Value::Bool(_) if INT_DATA.contains(&attr) => {
            let i = whole_index(target).unwrap_or(0);
            return Ok(Value::Int(match attr {
                "imag" => 0,
                "denominator" => 1,
                _ => i,
            }));
        }
        Value::Big(_) if INT_DATA.contains(&attr) => {
            return Ok(match attr {
                "imag" => Value::Int(0),
                "denominator" => Value::Int(1),
                _ => target.clone(),
            })
        }
        Value::Float(f) if attr == "real" || attr == "imag" => {
            return Ok(Value::Float(if attr == "real" { *f } else { 0.0 }))
        }
        _ => {}
    }
    let names = host.names_of(target)?;
    if names.iter().any(|n| n == attr) {
        return err(format!(
            "attribute {} is a method, not data; expressions read values, they do not pass functions around",
            str_repr(attr)
        ));
    }
    if let Value::List(x) | Value::Tuple(x) = target {
        return err(format!(
            "{} of {} items has no {}; use .length for the count, or the query's <name>_result for its metadata",
            type_name(target),
            x.len(),
            str_repr(attr)
        ));
    }
    undefined(format!(
        "attribute {} not found on {}{}",
        str_repr(attr),
        type_name(target),
        suggest(attr, names)
    ))
}

/// Python can hash it (a record's key): not a list, a record, nor a tuple holding one.
fn hashable(v: &Value) -> bool {
    match v {
        Value::List(_) | Value::Map(_) | Value::Entity(_) => false,
        Value::Tuple(x) => x.iter().all(hashable),
        _ => true,
    }
}

/// The type Python names when it cannot hash a value: the first unhashable thing in it.
fn unhashable_in(v: &Value) -> &'static str {
    match v {
        Value::Tuple(x) => x
            .iter()
            .find(|i| !hashable(i))
            .map_or("tuple", unhashable_in),
        other => type_name(other),
    }
}

fn index(host: &mut dyn Host, target: &Value, key: &Value) -> Result<Value, VmError> {
    if matches!(target, Value::Map(_) | Value::Entity(_)) {
        if !hashable(key) {
            return err(format!(
                "cannot index: unhashable type: '{}'",
                unhashable_in(key)
            ));
        }
        let found = match (target, key) {
            (Value::Map(m), Value::Str(k)) => m.get(k).cloned(),
            (Value::Entity(id), Value::Str(k)) => host.field(id, k)?,
            _ => None,
        };
        return match found {
            Some(v) => Ok(v),
            None => {
                let hint = match key {
                    Value::Str(k) => suggest(k, host.names_of(target)?),
                    _ => String::new(),
                };
                undefined(format!("key {} not found{hint}", py_repr(key)))
            }
        };
    }
    match target {
        Value::List(x) | Value::Tuple(x) => {
            let Some(i) = whole_index(key) else {
                if let Value::Big(_) = key {
                    return undefined("cannot index: cannot fit 'int' into an index-sized integer");
                }
                return err(format!(
                    "cannot index: {} indices must be integers or slices, not {}",
                    type_name(target),
                    type_name(key)
                ));
            };
            let n = x.len() as i64;
            let j = if i < 0 { i + n } else { i };
            if j < 0 || j >= n {
                return undefined(format!(
                    "cannot index: {} index out of range",
                    type_name(target)
                ));
            }
            Ok(x[j as usize].clone())
        }
        Value::Str(s) => {
            let Some(i) = whole_index(key) else {
                return err(format!(
                    "cannot index: string indices must be integers, not '{}'",
                    type_name(key)
                ));
            };
            let chars: Vec<char> = s.chars().collect();
            let n = chars.len() as i64;
            let j = if i < 0 { i + n } else { i };
            if j < 0 || j >= n {
                return undefined("cannot index: string index out of range");
            }
            Ok(Value::Str(chars[j as usize].to_string()))
        }
        other => err(format!(
            "cannot index: '{}' object is not subscriptable",
            type_name(other)
        )),
    }
}

fn slice_bound(v: Option<Value>) -> Result<Option<i64>, VmError> {
    match v {
        None | Some(Value::Null) => Ok(None),
        Some(b) => match whole_index(&b) {
            Some(i) => Ok(Some(i)),
            None => err(
                "cannot index: slice indices must be integers or None or have an __index__ method",
            ),
        },
    }
}

fn slice(target: &Value, lower: Option<Value>, upper: Option<Value>) -> Result<Value, VmError> {
    match target {
        Value::Map(_) | Value::Entity(_) => {
            // a slice is no record's key (Python 3.12 hashes it, by its bounds)
            if let Some(b) = lower.iter().chain(upper.iter()).find(|b| !hashable(b)) {
                return err(format!(
                    "cannot index: unhashable type: '{}'",
                    unhashable_in(b)
                ));
            }
            let bound = |b: &Option<Value>| b.as_ref().map_or("None".to_string(), py_repr);
            return undefined(format!(
                "key slice({}, {}, None) not found",
                bound(&lower),
                bound(&upper)
            ));
        }
        Value::List(_) | Value::Tuple(_) | Value::Str(_) => {}
        other => {
            return err(format!(
                "cannot index: '{}' object is not subscriptable",
                type_name(other)
            ))
        }
    }
    let (lo, hi) = (slice_bound(lower)?, slice_bound(upper)?);
    let range = |n: usize| -> (usize, usize) {
        let n = n as i64;
        let fix = |b: Option<i64>, d: i64| -> i64 {
            match b {
                None => d,
                Some(i) if i < 0 => (i + n).max(0),
                Some(i) => i.min(n),
            }
        };
        let (a, b) = (fix(lo, 0), fix(hi, n));
        (a as usize, (b.max(a)) as usize)
    };
    match target {
        Value::List(x) => {
            let (a, b) = range(x.len());
            Ok(Value::List(x[a..b].to_vec()))
        }
        Value::Tuple(x) => {
            let (a, b) = range(x.len());
            Ok(Value::Tuple(x[a..b].to_vec()))
        }
        Value::Str(s) => {
            let chars: Vec<char> = s.chars().collect();
            let (a, b) = range(chars.len());
            Ok(Value::Str(chars[a..b].iter().collect()))
        }
        other => err(format!(
            "cannot index: '{}' object is not subscriptable",
            type_name(other)
        )),
    }
}

// -- running -------------------------------------------------------------------------------------------------------

/// The block's own variables (a q:command's me and its arguments, a view's it and me), by name.
pub type Locals = Map;

/// A q:function the machine holds: its block's code, its parameters, its line.
#[derive(Debug)]
pub struct Function {
    pub name: String,
    pub code: Arc<Code>,
    pub params: Vec<String>,
    pub line: u32,
}

/// The world's q:functions, by name.
pub type Functions = HashMap<String, Arc<Function>>;

/// A q:loop's turns: what is left of its items, and its variables' names.
struct Turns {
    items: std::vec::IntoIter<Value>,
    at: i64,
    var: usize,
    index: Option<usize>,
}

fn short() -> VmError {
    VmError::new(ErrorKind::Expression, "the machine's stack is short")
}

/// The machine, for a run: the world's q:functions, and how deep their calls are. The depth is the world's, not
/// the run's (rules.py's Interpreter.depth): a block the world runs from inside an effect (a q:kill's on-death)
/// counts on from where its caller was.
pub struct Machine<'a> {
    pub functions: &'a Functions,
    pub depth: &'a AtomicUsize,
}

impl Machine<'_> {
    /// Runs a code, an expression's or a block's: the expression's value; the block's q:return, or null when it
    /// ends. An error says the line of the statement it came from.
    pub fn run(
        &self,
        code: &Code,
        locals: &mut Locals,
        host: &mut dyn Host,
    ) -> Result<Value, VmError> {
        let mut line = 0u32;
        self.frame(code, locals, host, &mut line).map_err(|mut e| {
            if e.line.is_none() {
                e.line = Some(line);
            }
            e
        })
    }

    /// rules.py's Interpreter.call: so many arguments as parameters, MAX_DEPTH deep at most, the q:return's value
    /// or null. An error says `line` (the q:call's, or for a call in an expression the q:function's own).
    fn call(
        &self,
        name: &str,
        args: Vec<Value>,
        line: u32,
        host: &mut dyn Host,
    ) -> Result<Value, VmError> {
        let Some(function) = self.functions.get(name) else {
            return err(format!("function {} is not defined", str_repr(name)));
        };
        let placed = |message: String| VmError {
            kind: ErrorKind::Rule,
            message,
            line: Some(line),
        };
        if args.len() != function.params.len() {
            return Err(placed(format!(
                "{}() takes {} arguments ({}), not {}",
                function.name,
                function.params.len(),
                if function.params.is_empty() {
                    "none".to_string()
                } else {
                    function.params.join(", ")
                },
                args.len()
            )));
        }
        if self.depth.load(Relaxed) >= MAX_DEPTH {
            return Err(placed(format!(
                "{}(): calls nested {MAX_DEPTH} deep",
                function.name
            )));
        }
        self.depth.fetch_add(1, Relaxed);
        let mut locals: Locals = function.params.iter().cloned().zip(args).collect();
        let result = self.run(&function.code, &mut locals, host);
        self.depth.fetch_sub(1, Relaxed);
        result
    }

    fn frame(
        &self,
        code: &Code,
        locals: &mut Locals,
        host: &mut dyn Host,
        line: &mut u32,
    ) -> Result<Value, VmError> {
        let mut stack: Vec<Value> = Vec::with_capacity(16);
        let mut loops: Vec<Turns> = Vec::new();
        let mut pc = 0usize;
        macro_rules! pop {
            () => {
                stack.pop().ok_or_else(short)?
            };
        }
        macro_rules! pop_n {
            ($n:expr) => {{
                let n = $n;
                if stack.len() < n {
                    return Err(short());
                }
                stack.split_off(stack.len() - n)
            }};
        }
        while pc < code.ops.len() {
            let (op, a, b) = code.ops[pc];
            pc += 1;
            match op {
                Op::Const => stack.push(code.consts[a as usize].clone()),
                Op::Name => {
                    let name = &code.names[a as usize];
                    let value = match locals.get(name) {
                        Some(v) => v.clone(),
                        None => match host.variable(name) {
                            Some(v) => v,
                            None => match name.as_str() {
                                "true" => Value::Bool(true),
                                "false" => Value::Bool(false),
                                "null" => Value::Null,
                                _ => {
                                    let names = host.scope_names(locals);
                                    return undefined(format!(
                                        "variable {} is not defined{}",
                                        str_repr(name),
                                        suggest(name, names)
                                    ));
                                }
                            },
                        },
                    };
                    stack.push(value);
                }
                Op::Attr => {
                    let target = pop!();
                    stack.push(attribute(host, &target, &code.names[a as usize])?);
                }
                Op::Index => {
                    let key = pop!();
                    let target = pop!();
                    stack.push(index(host, &target, &key)?);
                }
                Op::Slice => {
                    let upper = if a & 2 != 0 { Some(pop!()) } else { None };
                    let lower = if a & 1 != 0 { Some(pop!()) } else { None };
                    let target = pop!();
                    stack.push(slice(&target, lower, upper)?);
                }
                Op::BinOp => {
                    let right = pop!();
                    let left = pop!();
                    stack.push(binop(a, left, right)?);
                }
                Op::Unary => {
                    let v = pop!();
                    stack.push(unary(a, v)?);
                }
                Op::Compare => {
                    let right = pop!();
                    let left = pop!();
                    stack.push(Value::Bool(compare(host, a, &left, &right)?));
                }
                Op::Jump => pc = a as usize,
                Op::JumpIfFalse => {
                    if !truthy(&pop!()) {
                        pc = a as usize;
                    }
                }
                Op::JumpIfFalseOrPop | Op::JumpIfTrueOrPop => {
                    let top = stack.last().map(truthy).unwrap_or(false);
                    if top == (op == Op::JumpIfTrueOrPop) {
                        pc = a as usize;
                    } else {
                        pop!();
                    }
                }
                Op::Dup => {
                    let top = stack.last().cloned().ok_or_else(short)?;
                    stack.push(top);
                }
                Op::Rot2 => {
                    let n = stack.len();
                    if n < 2 {
                        return err("the machine's stack is short");
                    }
                    stack.swap(n - 1, n - 2);
                }
                Op::Rot3 => {
                    let c = pop!();
                    let b2 = pop!();
                    let a2 = pop!();
                    stack.push(c);
                    stack.push(a2);
                    stack.push(b2);
                }
                Op::Pop => {
                    pop!();
                }
                Op::List | Op::Tuple => {
                    let items = pop_n!(a as usize);
                    stack.push(if op == Op::List {
                        Value::List(items)
                    } else {
                        Value::Tuple(items)
                    });
                }
                Op::Dict => {
                    let flat = pop_n!(a as usize * 2);
                    let mut map = Map::with_capacity(a as usize);
                    let mut it = flat.into_iter();
                    while let (Some(k), Some(v)) = (it.next(), it.next()) {
                        match k {
                            Value::Str(k) => {
                                map.insert(k, v);
                            }
                            other => {
                                return err(format!(
                                    "a record's keys are texts, not {} (a world keeps texts)",
                                    type_name(&other)
                                ))
                            }
                        }
                    }
                    stack.push(Value::Map(map));
                }
                Op::Call | Op::CallHost | Op::CallKw | Op::CallHostKw => {
                    let name = &code.names[a as usize];
                    let (count, keywords): (usize, Vec<String>) =
                        if matches!(op, Op::Call | Op::CallHost) {
                            (b as usize, vec![])
                        } else {
                            match &code.consts[b as usize] {
                                Value::List(spec) if spec.len() == 2 => {
                                    let count = whole_index(&spec[0]).unwrap_or(0) as usize;
                                    let names = match &spec[1] {
                                        Value::List(n) => n.iter().map(py_str).collect(),
                                        _ => vec![],
                                    };
                                    (count, names)
                                }
                                _ => return err("a call's keywords are not its"),
                            }
                        };
                    let mut values = pop_n!(count + keywords.len());
                    let kwvalues = values.split_off(count);
                    let kwargs: Vec<(String, Value)> = keywords.into_iter().zip(kwvalues).collect();
                    let result = if matches!(op, Op::CallHost | Op::CallHostKw) {
                        host.call(name, values, kwargs)?
                    } else {
                        native(host, name, values, kwargs)?
                    };
                    stack.push(result);
                }

                Op::StoreName => {
                    let value = pop!();
                    let name = &code.names[a as usize];
                    if let Some(slot) = locals.get_mut(name) {
                        *slot = value;
                    } else if !host.write_var(name, &value, *line)? {
                        locals.insert(name.clone(), value);
                    }
                }
                Op::StorePath => {
                    let value = pop!();
                    let root = match &code.consts[a as usize] {
                        Value::List(parts) if !parts.is_empty() => py_str(&parts[0]),
                        _ => String::new(),
                    };
                    let held = locals.get(&root).cloned();
                    let local = held.is_some();
                    let name = py_str(&code.consts[b as usize]);
                    if let Some(changed) = host.assign_path(&name, held, value, *line)? {
                        if local {
                            locals.insert(root, changed);
                        }
                    }
                }
                Op::Format => {
                    let parts = pop_n!(a as usize);
                    let mut out = String::new();
                    for part in &parts {
                        out.push_str(&text_of(host, part)?);
                    }
                    stack.push(Value::Str(out));
                }
                Op::LoopItems => {
                    let items = match pop!() {
                        Value::List(x) | Value::Tuple(x) => x,
                        Value::Map(m) => m.into_values().collect(),
                        Value::Entity(id) => {
                            let mut values = Vec::new();
                            for key in host.keys(&id)? {
                                values.push(host.field(&id, &key)?.unwrap_or(Value::Null));
                            }
                            values
                        }
                        Value::Str(s) => s.chars().map(|c| Value::Str(c.to_string())).collect(),
                        other => {
                            return rule(format!(
                                "q:loop items= is not a list ({})",
                                type_name(&other)
                            ))
                        }
                    };
                    loops.push(turns(items, a, b)?);
                }
                Op::LoopRange => {
                    let last = pop!();
                    let first = py_int(&pop!())?;
                    let last = py_int(&last)?;
                    let count = (i128::from(last) + 1 - i128::from(first)).max(0);
                    if count > MAX_LOOP as i128 {
                        return loop_too_long(count);
                    }
                    loops.push(turns((first..=last).map(Value::Int).collect(), a, b)?);
                }
                Op::ForNext => {
                    let turn = loops.last_mut().ok_or_else(short)?;
                    match turn.items.next() {
                        Some(item) => {
                            locals.insert(code.names[turn.var].clone(), item);
                            if let Some(index) = turn.index {
                                locals.insert(code.names[index].clone(), Value::Int(turn.at));
                            }
                            turn.at += 1;
                        }
                        None => {
                            loops.pop();
                            pc = a as usize;
                        }
                    }
                }
                Op::CallUser => {
                    // as the Core calls a function: what goes wrong in it is said as `name() failed: ...`
                    let name = &code.names[a as usize];
                    let args = pop_n!(b as usize);
                    let Some(function) = self.functions.get(name) else {
                        return err(format!("function {} is not defined", str_repr(name)));
                    };
                    let value = self.call(name, args, function.line, host).map_err(|e| {
                        VmError::new(
                            ErrorKind::Expression,
                            format!("{name}() failed: {}", e.text()),
                        )
                    })?;
                    stack.push(value);
                }
                Op::CallStatement => {
                    let args = pop_n!(b as usize);
                    let value = self.call(&code.names[a as usize], args, *line, host)?;
                    stack.push(value);
                }
                Op::Return => return Ok(pop!()),
                Op::Refuse => {
                    let reason = pop!();
                    return Err(VmError::new(ErrorKind::Refused, text_of(host, &reason)?));
                }
                Op::Effect => {
                    let args = pop_n!(b as usize);
                    host.effect(&py_str(&code.consts[a as usize]), args)?;
                }
                Op::Line => *line = a,
                Op::LocalOrNull => stack.push(
                    locals
                        .get(&code.names[a as usize])
                        .cloned()
                        .unwrap_or(Value::Null),
                ),
                Op::Fail => return rule(py_str(&code.consts[a as usize])),
            }
        }
        // an expression leaves its value; a block, nothing: a q:function that ends with no q:return gives null
        Ok(stack.pop().unwrap_or(Value::Null))
    }
}

/// An expression run alone: no q:functions of the machine's (the host has them all).
pub fn run(code: &Code, locals: &Locals, host: &mut dyn Host) -> Result<Value, VmError> {
    let functions = Functions::new();
    let depth = AtomicUsize::new(0);
    Machine {
        functions: &functions,
        depth: &depth,
    }
    .run(code, &mut locals.clone(), host)
}

fn loop_too_long<T>(count: impl std::fmt::Display) -> Result<T, VmError> {
    rule(format!(
        "q:loop of {count} turns: a tick holds {MAX_LOOP} at most"
    ))
}

fn turns(items: Vec<Value>, var: u32, index: u32) -> Result<Turns, VmError> {
    if items.len() > MAX_LOOP {
        return loop_too_long(items.len());
    }
    Ok(Turns {
        items: items.into_iter(),
        at: 0,
        var: var as usize,
        index: (index != NO_INDEX).then_some(index as usize),
    })
}

/// Python's int(x), as q:loop from= and to= take it: what it raises, Python's own errors.
fn py_int(v: &Value) -> Result<i64, VmError> {
    match v {
        Value::Int(i) => Ok(*i),
        Value::Bool(b) => Ok(i64::from(*b)),
        Value::Big(_) => big_refused(),
        Value::Float(f) if f.is_nan() => raise(Raise::Value, "cannot convert float NaN to integer"),
        Value::Float(f) if f.is_infinite() => {
            raise(Raise::Overflow, "cannot convert float infinity to integer")
        }
        Value::Float(f) if f.trunc().abs() >= TWO_63 => big_refused(),
        Value::Float(f) => Ok(f.trunc() as i64),
        Value::Str(s) => match parse_int(s) {
            Some(Value::Int(i)) => Ok(i),
            Some(_) => big_refused(),
            None => raise(
                Raise::Value,
                format!("invalid literal for int() with base 10: {}", str_repr(s)),
            ),
        },
        other => raise(
            Raise::Type,
            format!(
                "int() argument must be a string, a bytes-like object or a real number, not '{}'",
                type_name(other)
            ),
        ),
    }
}

/// expressions.py's text_of: 3 for 3.0, true and false, nothing for null; the rest as Python's str() says it (an
/// entity as the world's dict).
fn text_of(host: &mut dyn Host, v: &Value) -> Result<String, VmError> {
    Ok(match v {
        Value::Null => String::new(),
        Value::Bool(true) => "true".into(),
        Value::Bool(false) => "false".into(),
        Value::Float(f) if f.is_finite() && f.fract() == 0.0 => whole_float_text(*f),
        Value::Str(s) => s.clone(),
        other => py_str(&materialize(host, other)?),
    })
}

/// str(int(f)) of a whole float: to the digit, however large.
fn whole_float_text(f: f64) -> String {
    if f.abs() < TWO_63 {
        return (f as i64).to_string();
    }
    let bits = f.to_bits();
    let shift = ((bits >> 52) & 0x7ff) as i32 - 1075; // f is mantissa * 2^shift, and shift > 0 here
    let mantissa = (bits & ((1u64 << 52) - 1)) | (1u64 << 52);
    let mut digits: Vec<u8> = mantissa
        .to_string()
        .bytes()
        .rev()
        .map(|d| d - b'0')
        .collect();
    for _ in 0..shift {
        let mut carry = 0u8;
        for d in digits.iter_mut() {
            let x = *d * 2 + carry;
            *d = x % 10;
            carry = x / 10;
        }
        if carry > 0 {
            digits.push(carry);
        }
    }
    let text: String = digits.iter().rev().map(|d| char::from(b'0' + d)).collect();
    if f < 0.0 {
        format!("-{text}")
    } else {
        text
    }
}

/// A value with its entities as the world's dicts (their fields, as they are now).
fn materialize(host: &mut dyn Host, v: &Value) -> Result<Value, VmError> {
    Ok(match v {
        Value::Entity(id) => {
            let mut fields = Map::new();
            for key in host.keys(id)? {
                let value = host.field(id, &key)?.unwrap_or(Value::Null);
                fields.insert(key, materialize(host, &value)?);
            }
            Value::Map(fields)
        }
        Value::List(x) => Value::List(
            x.iter()
                .map(|i| materialize(host, i))
                .collect::<Result<_, _>>()?,
        ),
        Value::Tuple(x) => Value::Tuple(
            x.iter()
                .map(|i| materialize(host, i))
                .collect::<Result<_, _>>()?,
        ),
        Value::Map(m) => {
            let mut out = Map::with_capacity(m.len());
            for (k, i) in m {
                out.insert(k.clone(), materialize(host, i)?);
            }
            Value::Map(out)
        }
        other => other.clone(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    struct NoWorld;
    impl Host for NoWorld {
        fn variable(&mut self, _: &str) -> Option<Value> {
            None
        }
        fn field(&mut self, _: &str, _: &str) -> Result<Option<Value>, VmError> {
            Ok(None)
        }
        fn keys(&mut self, _: &str) -> Result<Vec<String>, VmError> {
            Ok(vec![])
        }
        fn call(
            &mut self,
            name: &str,
            _: Vec<Value>,
            _: Vec<(String, Value)>,
        ) -> Result<Value, VmError> {
            err(format!("function {name:?} is not defined"))
        }
    }

    fn code(ops: &[(Op, u32, u32)], consts: Vec<Value>, names: &[&str]) -> Arc<Code> {
        let code = Code {
            ops: ops.to_vec(),
            consts,
            names: names.iter().map(|n| n.to_string()).collect(),
        };
        code.check().unwrap();
        Arc::new(code)
    }

    #[test]
    fn a_block_loops_and_calls_its_functions() {
        use Op::*;
        // add(a, b): return a + b
        let add = code(
            &[(Name, 0, 0), (Name, 1, 0), (BinOp, 0, 0), (Return, 0, 0)],
            vec![],
            &["a", "b"],
        );
        // down(n): q:call down(n), with no end
        let down = code(
            &[(Name, 0, 0), (CallStatement, 1, 1), (Pop, 0, 0)],
            vec![],
            &["n", "down"],
        );
        let mut functions = Functions::new();
        for (name, body, params) in [("add", add, vec!["a", "b"]), ("down", down, vec!["n"])] {
            let function = Function {
                name: name.into(),
                code: body,
                params: params.into_iter().map(String::from).collect(),
                line: 7,
            };
            functions.insert(name.into(), Arc::new(function));
        }
        // t = 0; q:loop k from 1 to 4: t = add(t, k); return t
        let block = code(
            &[
                (Line, 3, 0),
                (Const, 0, 0),
                (StoreName, 0, 0),
                (Const, 1, 0),
                (Const, 2, 0),
                (LoopRange, 1, NO_INDEX),
                (ForNext, 13, 0),
                (Line, 4, 0),
                (Name, 0, 0),
                (Name, 1, 0),
                (CallUser, 2, 2),
                (StoreName, 0, 0),
                (Jump, 6, 0),
                (Name, 0, 0),
                (Return, 0, 0),
            ],
            vec![Value::Int(0), Value::Int(1), Value::Int(4)],
            &["t", "k", "add"],
        );
        let depth = AtomicUsize::new(0);
        let machine = Machine {
            functions: &functions,
            depth: &depth,
        };
        let mut locals = Locals::new();
        let total = machine.run(&block, &mut locals, &mut NoWorld).unwrap();
        assert!(py_eq(&total, &Value::Int(10)));
        assert!(py_eq(&locals["k"], &Value::Int(4)));
        // a call too deep: said at the q:call's line, and the depth back where it was
        let deep = code(
            &[
                (Line, 9, 0),
                (Const, 0, 0),
                (CallStatement, 0, 1),
                (Pop, 0, 0),
            ],
            vec![Value::Int(1)],
            &["down"],
        );
        let e = machine
            .run(&deep, &mut Locals::new(), &mut NoWorld)
            .unwrap_err();
        assert_eq!((e.kind, e.line), (ErrorKind::Rule, Some(0)));
        assert_eq!(e.text(), "down(): calls nested 64 deep");
        assert_eq!(depth.load(Relaxed), 0);
        // a function that fails in an expression is said as the Core says it
        let short = code(
            &[(Line, 5, 0), (Const, 0, 0), (CallUser, 0, 1)],
            vec![Value::Int(1)],
            &["add"],
        );
        let e = machine
            .run(&short, &mut Locals::new(), &mut NoWorld)
            .unwrap_err();
        assert_eq!(e.kind, ErrorKind::Expression);
        assert_eq!(
            e.text(),
            "line 5: add() failed: line 7: add() takes 2 arguments (a, b), not 1"
        );
    }

    #[test]
    fn suggestions_as_difflib_makes_them() {
        let names = |n: &[&str]| n.iter().map(|s| s.to_string()).collect::<Vec<_>>();
        assert_eq!(
            suggest("step", names(&["steps", "name"])),
            ", did you mean 'steps'?"
        );
        assert_eq!(suggest("k", names(&["j"])), " (in scope: j)");
        assert_eq!(
            suggest("lenght", names(&["length", "height", "light"])),
            ", did you mean 'length' or 'light' or 'height'?"
        );
        assert_eq!(suggest("x", vec![]), "");
        assert_eq!(whole_float_text(1e20), "100000000000000000000");
        assert_eq!(whole_float_text(-2f64.powi(70)), "-1180591620717411303424");
    }

    #[test]
    fn numbers_as_python_has_them() {
        let h = &mut NoWorld;
        let b = |op, l, r| binop(op, l, r).unwrap();
        assert!(py_eq(
            &b(0, Value::Str("5".into()), Value::Int(3)),
            &Value::Int(8)
        ));
        assert!(py_eq(&b(4, Value::Int(-7), Value::Int(2)), &Value::Int(-4)));
        assert!(py_eq(&b(5, Value::Int(-7), Value::Int(2)), &Value::Int(1)));
        assert!(py_eq(
            &b(5, Value::Float(-7.5), Value::Int(2)),
            &Value::Float(0.5)
        ));
        assert!(py_eq(
            &b(3, Value::Int(1), Value::Int(2)),
            &Value::Float(0.5)
        ));
        assert!(binop(0, Value::Bool(true), Value::Int(1)).is_err());
        assert!(compare(h, 4, &Value::Str("10".into()), &Value::Str("9".into())).unwrap());
        assert!(compare(
            h,
            6,
            &Value::Str("5".into()),
            &Value::List(vec![Value::Int(5)])
        )
        .unwrap());
        assert!(py_eq(
            &round(&Value::Float(2.5), 0).unwrap(),
            &Value::Int(3)
        ));
        assert!(py_eq(
            &round(&Value::Float(0.125), 2).unwrap(),
            &Value::Float(0.13)
        ));
        assert!(py_eq(
            &round(&Value::Float(-2.5), 0).unwrap(),
            &Value::Int(-3)
        ));
        assert_eq!(
            py_str(&Value::List(vec![
                Value::Str("a'".into()),
                Value::Float(1.0),
                Value::Null
            ])),
            "[\"a'\", 1.0, None]"
        );
    }
}

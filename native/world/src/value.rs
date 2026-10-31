//! A world's value as the engine holds it: what Python's world keeps (numbers, texts, true, false, null, lists and
//! records), compared as Python compares them and written as Python's `json.dumps` writes them, byte for byte.

use indexmap::IndexMap;

/// A record, in the order Python's dict keeps it (hashed with FxHash: the order is the map's, not the hash's).
pub type Map = IndexMap<String, Value, rustc_hash::FxBuildHasher>;

#[derive(Clone, Debug)]
pub enum Value {
    Null,
    Bool(bool),
    Int(i64),
    /// A whole number past 64 bits, as Python writes it (Python's are unbounded).
    Big(String),
    Float(f64),
    Str(String),
    List(Vec<Value>),
    /// A tuple: a list to JSON, but not equal to one (Python's `(1, 2) != [1, 2]`).
    Tuple(Vec<Value>),
    Map(Map),
    /// A value only Python could write (a text with a lone surrogate): its JSON, as Python made it.
    Json(String),
    /// An entity of the world, by its id: the machine reads its fields through its host (vm.rs).
    Entity(String),
}

impl Value {
    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Map(m) => m.get(key),
            _ => None,
        }
    }

    /// Python's `int(x)` of a number (a bool is one); None of anything else.
    pub fn as_whole(&self) -> Option<i64> {
        match self {
            Value::Int(i) => Some(*i),
            Value::Bool(b) => Some(*b as i64),
            Value::Float(f) if f.is_finite() => Some(f.trunc() as i64),
            _ => None,
        }
    }
}

/// Python's `a == b` of two world values: 1 == 1.0 == True, a record's keys in any order.
pub fn py_eq(a: &Value, b: &Value) -> bool {
    use Value::*;
    match (a, b) {
        (Null, Null) => true,
        (Str(x), Str(y)) => x == y,
        (Json(x), Json(y)) => x == y,
        (Big(x), Big(y)) => x == y,
        (List(x), List(y)) | (Tuple(x), Tuple(y)) => {
            x.len() == y.len() && x.iter().zip(y).all(|(p, q)| py_eq(p, q))
        }
        (Entity(x), Entity(y)) => x == y,
        (Map(x), Map(y)) => {
            x.len() == y.len() && x.iter().all(|(k, v)| y.get(k).is_some_and(|w| py_eq(v, w)))
        }
        (Bool(_) | Int(_), Bool(_) | Int(_)) => a.as_whole() == b.as_whole(),
        (Float(x), Float(y)) => x == y,
        (Float(f), Bool(_) | Int(_)) => int_eq_float(b.as_whole().unwrap(), *f),
        (Bool(_) | Int(_), Float(f)) => int_eq_float(a.as_whole().unwrap(), *f),
        _ => false,
    }
}

fn int_eq_float(i: i64, f: f64) -> bool {
    // exactly, as Python does: 2**53 + 1 is not 2.0**53
    f.is_finite()
        && f.fract() == 0.0
        && (-9.223_372_036_854_776e18..9.223_372_036_854_776e18).contains(&f)
        && f as i64 == i
}

/// The fields of `now` that are not in `before` as they are now (frames.py's `_changed`), in `now`'s order.
pub fn changed<'a>(before: &Map, now: &'a Map) -> Vec<(&'a String, &'a Value)> {
    now.iter()
        .filter(|(k, v)| !before.get(*k).is_some_and(|b| py_eq(b, v)))
        .collect()
}

// -- JSON, as Python's json.dumps(value, separators=(',', ':')) writes it ------------------------------------------

pub fn write_json(value: &Value, out: &mut String) {
    match value {
        Value::Null => out.push_str("null"),
        Value::Bool(true) => out.push_str("true"),
        Value::Bool(false) => out.push_str("false"),
        Value::Int(i) => out.push_str(&i.to_string()),
        Value::Big(digits) => out.push_str(digits),
        Value::Float(f) => write_float(*f, out),
        Value::Str(s) => write_str(s, out),
        Value::Json(text) => out.push_str(text),
        Value::Entity(id) => write_str(id, out),
        Value::List(items) | Value::Tuple(items) => {
            out.push('[');
            for (n, item) in items.iter().enumerate() {
                if n > 0 {
                    out.push(',');
                }
                write_json(item, out);
            }
            out.push(']');
        }
        Value::Map(map) => write_map(map, out),
    }
}

pub fn write_map(map: &Map, out: &mut String) {
    out.push('{');
    for (n, (k, v)) in map.iter().enumerate() {
        if n > 0 {
            out.push(',');
        }
        write_str(k, out);
        out.push(':');
        write_json(v, out);
    }
    out.push('}');
}

/// A text with ensure_ascii's escapes: `"`, `\`, the usual controls, and \uXXXX (lower case) for anything not
/// printable ASCII, astral ones as their surrogate pair.
pub fn write_str(s: &str, out: &mut String) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            ' '..='~' => out.push(c),
            _ => {
                let mut units = [0u16; 2];
                for unit in c.encode_utf16(&mut units) {
                    out.push_str(&format!("\\u{:04x}", unit));
                }
            }
        }
    }
    out.push('"');
}

/// A float as Python's repr writes it: the shortest digits that read back the same, fixed between 1e-4 and 1e16,
/// else with an exponent of a sign and two digits at least (1e+16, 1.5e-05).
pub fn write_float(f: f64, out: &mut String) {
    if f == 0.0 {
        out.push_str(if f.is_sign_negative() { "-0.0" } else { "0.0" });
        return;
    }
    if f.is_nan() {
        out.push_str("NaN");
        return;
    }
    if f.is_infinite() {
        out.push_str(if f > 0.0 { "Infinity" } else { "-Infinity" });
        return;
    }
    if f < 0.0 {
        out.push('-');
    }
    let sci = format!("{:e}", f.abs()); // the shortest digits: "1.5e-7", "1e16"
    let (mantissa, exp) = sci.split_once('e').unwrap();
    let exp: i32 = exp.parse().unwrap();
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();
    if (-4..16).contains(&exp) {
        if exp >= 0 {
            let whole = exp as usize + 1;
            if digits.len() <= whole {
                out.push_str(&digits);
                out.extend(std::iter::repeat_n('0', whole - digits.len()));
                out.push_str(".0");
            } else {
                out.push_str(&digits[..whole]);
                out.push('.');
                out.push_str(&digits[whole..]);
            }
        } else {
            out.push_str("0.");
            out.extend(std::iter::repeat_n('0', (-exp - 1) as usize));
            out.push_str(&digits);
        }
    } else {
        out.push_str(&digits[..1]);
        if digits.len() > 1 {
            out.push('.');
            out.push_str(&digits[1..]);
        }
        out.push('e');
        out.push(if exp < 0 { '-' } else { '+' });
        out.push_str(&format!("{:02}", exp.abs()));
    }
}

pub fn to_json(value: &Value) -> String {
    let mut out = String::new();
    write_json(value, &mut out);
    out
}

/// A message read from a player (serde_json's value) as a world's value.
pub fn from_serde(value: &serde_json::Value) -> Value {
    match value {
        serde_json::Value::Null => Value::Null,
        serde_json::Value::Bool(b) => Value::Bool(*b),
        serde_json::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Value::Int(i)
            } else if let Some(u) = n.as_u64() {
                Value::Big(u.to_string())
            } else {
                Value::Float(n.as_f64().unwrap_or(f64::NAN))
            }
        }
        serde_json::Value::String(s) => Value::Str(s.clone()),
        serde_json::Value::Array(items) => Value::List(items.iter().map(from_serde).collect()),
        serde_json::Value::Object(map) => Value::Map(
            map.iter()
                .map(|(k, v)| (k.clone(), from_serde(v)))
                .collect(),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn float(f: f64) -> String {
        let mut s = String::new();
        write_float(f, &mut s);
        s
    }

    #[test]
    fn floats_read_as_pythons_repr() {
        let cases = [
            (1.0, "1.0"),
            (0.1, "0.1"),
            (100.0, "100.0"),
            (1.5, "1.5"),
            (-2.25, "-2.25"),
            (0.0001, "0.0001"),
            (0.00001, "1e-05"),
            (1.5e-7, "1.5e-07"),
            (1e16, "1e+16"),
            (1.2345678901234568e17, "1.2345678901234568e+17"),
            (9999999999999998.0, "9999999999999998.0"),
            (123456.789, "123456.789"),
            (1e100, "1e+100"),
            (-0.0, "-0.0"),
            (0.30000000000000004, "0.30000000000000004"),
        ];
        for (f, want) in cases {
            assert_eq!(float(f), want, "{f}");
        }
    }

    #[test]
    fn texts_escape_as_ensure_ascii() {
        let mut s = String::new();
        write_str("a\"b\\c\nd\u{7f}é😀\u{1}", &mut s);
        assert_eq!(s, r#""a\"b\\c\nd\u007f\u00e9\ud83d\ude00\u0001""#);
    }

    #[test]
    fn values_compare_as_python_compares_them() {
        assert!(py_eq(&Value::Int(1), &Value::Float(1.0)));
        assert!(py_eq(&Value::Int(1), &Value::Bool(true)));
        assert!(!py_eq(&Value::Int(1), &Value::Str("1".into())));
        assert!(!py_eq(
            &Value::Int(9007199254740993),
            &Value::Float(9007199254740992.0)
        ));
        let a = Value::Map(
            [
                ("x".to_string(), Value::Int(1)),
                ("y".to_string(), Value::Int(2)),
            ]
            .into_iter()
            .collect(),
        );
        let b = Value::Map(
            [
                ("y".to_string(), Value::Int(2)),
                ("x".to_string(), Value::Float(1.0)),
            ]
            .into_iter()
            .collect(),
        );
        assert!(py_eq(&a, &b));
        assert!(!py_eq(&Value::Null, &Value::Bool(false)));
    }
}

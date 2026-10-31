//! Players together in the engine (together.py): the chat, a party, a trade between two. The chat, the party and the
//! trade bring their own commands, run as any command is: as the player who sent it, whole or not at all. A trade
//! moves both sides on the ledger at once, once both players accept the same offers.

use super::*;

/// Python's str.isspace() (the characters str.strip() takes off).
pub(super) fn py_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

pub(super) fn py_strip(s: &str) -> &str {
    s.trim_matches(py_space)
}

/// A character of a word, as Python's re \w matches one.
fn word_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_'
}

fn lower(c: char) -> char {
    let mut l = c.to_lowercase();
    match (l.next(), l.next()) {
        (Some(x), None) => x,
        _ => c,
    }
}

/// re.sub(rf'(?i)\b{re.escape(word)}\b', '*' * len(word), text).
fn star(text: &str, word: &str) -> String {
    let t: Vec<char> = text.chars().collect();
    let w: Vec<char> = word.chars().collect();
    if w.is_empty() {
        return text.to_string();
    }
    let boundary = |i: usize| {
        let before = i > 0 && word_char(t[i - 1]);
        let after = i < t.len() && word_char(t[i]);
        before != after
    };
    let mut out = String::with_capacity(text.len());
    let mut i = 0;
    while i < t.len() {
        if i + w.len() <= t.len()
            && boundary(i)
            && boundary(i + w.len())
            && (0..w.len()).all(|k| t[i + k] == w[k] || lower(t[i + k]) == lower(w[k]))
        {
            out.extend(std::iter::repeat_n('*', w.len()));
            i += w.len();
        } else {
            out.push(t[i]);
            i += 1;
        }
    }
    out
}

fn ids_of(v: Option<&Value>) -> Vec<String> {
    match v {
        Some(Value::List(x)) => x.iter().map(vm::py_str).collect(),
        _ => Vec::new(),
    }
}

impl World {
    /// The name an entity shows (me.get('name', me['id'])).
    pub(super) fn shown(&self, id: &str) -> Value {
        self.field_of(id, "name")
            .cloned()
            .unwrap_or_else(|| Value::Str(id.to_string()))
    }

    pub(super) fn player_of(&self, id: &str) -> Option<String> {
        match self.field_of(id, "_player") {
            Some(Value::Str(a)) => Some(a.clone()),
            _ => None,
        }
    }

    /// The players of these entities that are in the world.
    fn players_of(&self, ids: &[String]) -> Vec<String> {
        ids.iter()
            .filter(|m| self.entities.contains_key(*m))
            .filter_map(|m| self.player_of(m))
            .collect()
    }

    /// The party an entity is in, by its id: (its id, the party).
    fn party_record(&self, id: &str) -> Option<(String, Map)> {
        let pid = match self.field_of(id, "party") {
            Some(Value::Str(p)) => p.clone(),
            _ => String::new(),
        };
        match self.parties.get(&pid) {
            Some(Value::Map(p)) => Some((pid, p.clone())),
            _ => None,
        }
    }

    pub(super) fn builtin(&mut self, name: &str, me: &str, args: &Value) -> Result<(), VmError> {
        let arg = |k: &str| match args {
            Value::Map(m) => m.get(k).cloned().unwrap_or(Value::Null),
            _ => Value::Null,
        };
        match name {
            "chat" => self.chat(me, &arg("channel"), &arg("text")),
            "whisper" => self.whisper(me, &arg("to"), &arg("text")),
            "party-invite" => self.party_invite(me, &arg("who")),
            "party-accept" => self.party_accept(me, &arg("who")),
            "party-leave" => self.party_leave(me),
            "trade-offer" => self.trade_offer(me, &arg("who"), &arg("gold"), &arg("items")),
            "trade-accept" => self.trade_accept(me, &arg("who")),
            "trade-cancel" => self.trade_cancel(me, &arg("who")),
            other => Err(rule_at(
                format!("no command {} of the world's own", vm::str_repr(other)),
                0,
            )),
        }
    }

    // -- the chat ----------------------------------------------------------------------------------------------------

    fn clean(&self, text: &Value) -> Result<String, VmError> {
        let Value::Str(s) = text else {
            return Err(refused("Say something."));
        };
        if py_strip(s).is_empty() {
            return Err(refused("Say something."));
        }
        let kept: String = s
            .chars()
            .filter(|c| !matches!(*c, '\0'..='\u{1f}' | '\u{7f}'))
            .collect();
        let mut out: String = py_strip(&kept).chars().take(MAX_LINE).collect();
        if let Some(chat) = &self.def.chat {
            for word in chat.words.iter() {
                out = star(&out, word);
            }
        }
        Ok(out)
    }

    fn chat(&mut self, me: &str, channel: &Value, text: &Value) -> Result<(), VmError> {
        let def = self.def.clone();
        let Some(chat) = def.chat.as_ref() else {
            return Err(rule_at("the world has no q:chat", 0));
        };
        let name = match channel {
            Value::Str(c) if chat.channels.contains_key(c) => c.clone(),
            _ => {
                let names: Vec<&str> = chat.channels.keys().map(String::as_str).collect();
                return Err(refused(format!(
                    "There is no channel {} ({}).",
                    vm::py_repr(channel),
                    names.join(", ")
                )));
            }
        };
        let line = entry(vec![
            ("channel", Value::Str(name.clone())),
            ("who", self.shown(me)),
            ("text", Value::Str(self.clean(text)?)),
        ]);
        let to = if name == "party" {
            let Some((_, party)) = self.party_record(me) else {
                return Err(refused("You are in no party."));
            };
            self.players_of(&ids_of(party.get("members")))
        } else if let Some(reach) = chat.channels[&name] {
            let mut to = Vec::new();
            if let Some(here) = self.entity_tile(me) {
                for id in self.near_ids(here, reach) {
                    let Some(player) = self.player_of(&id) else {
                        continue;
                    };
                    if let Some(there) = self.entity_tile(&id) {
                        if chebyshev(here, there) <= reach {
                            to.push(player);
                        }
                    }
                }
            }
            to
        } else {
            self.players.keys().cloned().collect()
        };
        self.tell("chat", line, to)
    }

    fn whisper(&mut self, me: &str, who: &Value, text: &Value) -> Result<(), VmError> {
        let Some(other) = self.hero_of(who) else {
            return Err(refused("Nobody of that name here."));
        };
        let line = entry(vec![
            ("channel", Value::Str("whisper".into())),
            ("who", self.shown(me)),
            ("to", self.shown(&other)),
            ("text", Value::Str(self.clean(text)?)),
        ]);
        let to = [self.player_of(me), self.player_of(&other)]
            .into_iter()
            .flatten()
            .collect();
        self.tell("chat", line, to)
    }

    // -- parties -----------------------------------------------------------------------------------------------------

    fn party_size(&self) -> usize {
        self.def.party_size.unwrap_or(0).max(0) as usize
    }

    fn party_invite(&mut self, me: &str, who: &Value) -> Result<(), VmError> {
        let other = match self.hero_of(who) {
            Some(o) if o != me => o,
            _ => return Err(refused("Nobody of that name here.")),
        };
        if self.field_of(&other, "party").is_some_and(vm::truthy) {
            return Err(refused(format!(
                "{} is in a party.",
                vm::py_str(&self.shown(&other))
            )));
        }
        let pid = match self.field_of(me, "party") {
            Some(p) if vm::truthy(p) => vm::py_str(p),
            _ => {
                let n = self.counters.get("party").copied().unwrap_or(0) + 1;
                self.counters.insert("party".into(), n);
                let pid = format!("party-{n}");
                self.put(
                    Root::Parties,
                    &pid,
                    Some(entry(vec![
                        ("members", Value::List(vec![Value::Str(me.to_string())])),
                        ("invited", Value::List(vec![])),
                    ])),
                );
                self.write_field(me, "party", Value::Str(pid.clone()), 0)?;
                pid
            }
        };
        let Some(Value::Map(party)) = self.parties.get(&pid).cloned() else {
            return Err(rule_at(
                format!("there is no party {}", vm::str_repr(&pid)),
                0,
            ));
        };
        if ids_of(party.get("members")).len() >= self.party_size() {
            return Err(refused("The party is full."));
        }
        let mut invited = ids_of(party.get("invited"));
        if !invited.contains(&other) {
            invited.push(other.clone());
            let mut party = party.clone();
            party.insert(
                "invited".into(),
                Value::List(invited.into_iter().map(Value::Str).collect()),
            );
            self.put(Root::Parties, &pid, Some(Value::Map(party)));
        }
        let to = [self.player_of(me), self.player_of(&other)]
            .into_iter()
            .flatten()
            .collect();
        self.tell(
            "party",
            entry(vec![
                ("invited", Value::Str(other)),
                ("by", Value::Str(me.to_string())),
                ("party", Value::Str(pid)),
            ]),
            to,
        )
    }

    fn party_accept(&mut self, me: &str, who: &Value) -> Result<(), VmError> {
        let other = self.hero_of(who);
        let found = other.as_deref().and_then(|o| self.party_record(o));
        let Some((pid, party)) = found else {
            return Err(refused("No one invited you."));
        };
        let invited = ids_of(party.get("invited"));
        if !invited.iter().any(|i| i == me) {
            return Err(refused("No one invited you."));
        }
        if self.field_of(me, "party").is_some_and(vm::truthy) {
            return Err(refused("You are in a party already."));
        }
        let mut members = ids_of(party.get("members"));
        if members.len() >= self.party_size() {
            return Err(refused("The party is full."));
        }
        members.push(me.to_string());
        let list = |v: Vec<String>| Value::List(v.into_iter().map(Value::Str).collect());
        self.put(
            Root::Parties,
            &pid,
            Some(entry(vec![
                ("members", list(members)),
                (
                    "invited",
                    list(invited.into_iter().filter(|i| i != me).collect()),
                ),
            ])),
        );
        self.write_field(me, "party", Value::Str(pid.clone()), 0)?;
        self.tell_party(
            &pid,
            entry(vec![
                ("joined", Value::Str(me.to_string())),
                ("party", Value::Str(pid.clone())),
            ]),
            Vec::new(),
        )
    }

    pub(super) fn party_leave(&mut self, me: &str) -> Result<(), VmError> {
        let Some((pid, party)) = self.party_record(me) else {
            return Err(refused("You are in no party."));
        };
        let members: Vec<String> = ids_of(party.get("members"))
            .into_iter()
            .filter(|m| m != me)
            .collect();
        self.write_field(me, "party", Value::Str(String::new()), 0)?;
        let extra = self.player_of(me).into_iter().collect();
        self.tell_party(
            &pid,
            entry(vec![
                ("left", Value::Str(me.to_string())),
                ("party", Value::Str(pid.clone())),
            ]),
            extra,
        )?;
        if members.len() <= 1 {
            for m in &members {
                if self.entities.contains_key(m) {
                    self.write_field(m, "party", Value::Str(String::new()), 0)?;
                }
            }
            self.put(Root::Parties, &pid, None);
        } else {
            let mut party = party;
            party.insert(
                "members".into(),
                Value::List(members.into_iter().map(Value::Str).collect()),
            );
            self.put(Root::Parties, &pid, Some(Value::Map(party)));
        }
        Ok(())
    }

    fn tell_party(&mut self, pid: &str, value: Value, extra: Vec<String>) -> Result<(), VmError> {
        let members = match self.parties.get(pid) {
            Some(Value::Map(p)) => ids_of(p.get("members")),
            _ => Vec::new(),
        };
        let mut to = self.players_of(&members);
        to.extend(extra);
        self.tell("party", value, to)
    }

    /// party_of(x): the party of x that is in the world (x alone, with no party).
    pub(super) fn party_of(&self, x: &Value) -> Vec<String> {
        let Some(id) = self.entity_from(x) else {
            return Vec::new();
        };
        match self.party_record(&id) {
            None => vec![id],
            Some((_, party)) => ids_of(party.get("members"))
                .into_iter()
                .filter(|m| self.entities.contains_key(m))
                .collect(),
        }
    }

    /// party_near(x, n): the party of x within n tiles of it.
    pub(super) fn party_near(
        &mut self,
        x: &Value,
        n: Option<&Value>,
    ) -> Result<Vec<String>, VmError> {
        let Some(id) = self.entity_from(x) else {
            return Ok(Vec::new());
        };
        let Some(here) = self.entity_tile(&id) else {
            return Ok(vec![id]);
        };
        let mut reach = None;
        let mut out = Vec::new();
        for member in self.party_of(x) {
            let Some(there) = self.entity_tile(&member) else {
                continue;
            };
            let r = match reach {
                Some(r) => r,
                None => {
                    let r = match n {
                        Some(n) => self.whole("party_near", n)?,
                        None => 10,
                    };
                    reach = Some(r);
                    r
                }
            };
            if chebyshev(here, there) <= r {
                out.push(member);
            }
        }
        Ok(out)
    }

    // -- trades ------------------------------------------------------------------------------------------------------

    fn trade_key(a: &str, b: &str) -> (String, Vec<String>) {
        let mut between = vec![a.to_string(), b.to_string()];
        between.sort();
        (between.join("|"), between)
    }

    fn trade_offer(
        &mut self,
        me: &str,
        who: &Value,
        gold: &Value,
        items: &Value,
    ) -> Result<(), VmError> {
        let other = match self.hero_of(who) {
            Some(o) if o != me => o,
            _ => return Err(refused("Nobody of that name here.")),
        };
        let currency = self.first_currency();
        let gold = match gold {
            Value::Int(i) => *i,
            Value::Float(f) if f.is_finite() && *f == f.trunc() => *f as i64,
            _ => -1,
        };
        if gold < 0 || (gold != 0 && currency.is_none()) {
            return Err(refused("gold is a whole number, 0 or more."));
        }
        let counts: Vec<(String, i64)> = match items {
            Value::Map(m) if m.values().all(|v| matches!(v, Value::Int(n) if *n > 0)) => m
                .iter()
                .map(|(k, v)| (k.clone(), v.as_whole().unwrap_or(0)))
                .collect(),
            _ => return Err(refused("items is a record of counts: {\"cheese\": 2}.")),
        };
        if let Some(c) = &currency {
            if self.held_by(me, c, true) < gold {
                return Err(refused(format!("Not enough {c}.")));
            }
        }
        for (item, n) in &counts {
            if self.held_by(me, item, false) < *n {
                return Err(refused(format!("Not enough {item}.")));
            }
        }
        let (key, between) = World::trade_key(me, &other);
        let mut trade = match self.trades.get(&key) {
            Some(Value::Map(t)) => t.clone(),
            _ => match entry(vec![
                (
                    "between",
                    Value::List(between.into_iter().map(Value::Str).collect()),
                ),
                ("offers", Value::Map(Map::default())),
                ("accepted", Value::List(vec![])),
            ]) {
                Value::Map(t) => t,
                _ => unreachable!(),
            },
        };
        let mut offers = match trade.get("offers") {
            Some(Value::Map(o)) => o.clone(),
            _ => Map::default(),
        };
        let mut sorted = counts;
        sorted.sort();
        offers.insert(
            me.to_string(),
            entry(vec![
                ("gold", Value::Int(gold)),
                (
                    "items",
                    Value::Map(
                        sorted
                            .into_iter()
                            .map(|(k, n)| (k, Value::Int(n)))
                            .collect(),
                    ),
                ),
            ]),
        );
        trade.insert("offers".into(), Value::Map(offers));
        trade.insert("accepted".into(), Value::List(vec![]));
        self.put(Root::Trades, &key, Some(Value::Map(trade)));
        self.tell_trade(&key)
    }

    fn trade_accept(&mut self, me: &str, who: &Value) -> Result<(), VmError> {
        let other = self.hero_of(who);
        let key = other
            .as_deref()
            .map_or_else(String::new, |o| World::trade_key(me, o).0);
        let Some(Value::Map(trade)) = self.trades.get(&key).cloned() else {
            return Err(refused("No trade with them."));
        };
        let other = other.unwrap_or_default();
        let mut accepted = ids_of(trade.get("accepted"));
        if !accepted.iter().any(|a| a == me) {
            accepted.push(me.to_string());
        }
        accepted.sort();
        accepted.dedup();
        if accepted.len() < 2 {
            let mut trade = trade;
            trade.insert(
                "accepted".into(),
                Value::List(accepted.into_iter().map(Value::Str).collect()),
            );
            self.put(Root::Trades, &key, Some(Value::Map(trade)));
            return self.tell_trade(&key);
        }
        let currency = self.first_currency().map_or(Value::Null, Value::Str);
        let offers = match trade.get("offers") {
            Some(Value::Map(o)) => o.clone(),
            _ => Map::default(),
        };
        for (giver, taker) in [
            (me.to_string(), other.clone()),
            (other.clone(), me.to_string()),
        ] {
            let (gold, items) = match offers.get(&giver) {
                Some(Value::Map(o)) => (
                    o.get("gold").cloned().unwrap_or(Value::Int(0)),
                    match o.get("items") {
                        Some(Value::Map(i)) => i.clone(),
                        _ => Map::default(),
                    },
                ),
                _ => (Value::Int(0), Map::default()),
            };
            if vm::truthy(&gold) {
                self.pay(&giver, &taker, &gold, &currency, 0)?;
            }
            for (item, n) in items.iter() {
                let n = n.as_whole().unwrap_or(0);
                if self.held_by(&giver, item, false) < n {
                    return Err(refused(format!(
                        "{} has not enough {item} now.",
                        vm::py_str(&self.shown(&giver))
                    )));
                }
                self.shift(&giver, item, -n, false, 0)?;
                self.shift(&taker, item, n, false, 0)?;
            }
        }
        self.put(Root::Trades, &key, None);
        let to = [self.player_of(me), self.player_of(&other)]
            .into_iter()
            .flatten()
            .collect();
        self.tell(
            "trade",
            entry(vec![
                (
                    "between",
                    trade.get("between").cloned().unwrap_or(Value::Null),
                ),
                ("done", Value::Bool(true)),
                ("offers", Value::Map(offers)),
            ]),
            to,
        )
    }

    fn trade_cancel(&mut self, me: &str, who: &Value) -> Result<(), VmError> {
        let key = self
            .hero_of(who)
            .map_or_else(String::new, |o| World::trade_key(me, &o).0);
        let Some(Value::Map(trade)) = self.trades.get(&key).cloned() else {
            return Err(refused("No trade with them."));
        };
        self.put(Root::Trades, &key, None);
        let to = self.players_of(&ids_of(trade.get("between")));
        self.tell(
            "trade",
            entry(vec![
                (
                    "between",
                    trade.get("between").cloned().unwrap_or(Value::Null),
                ),
                ("cancelled", Value::Bool(true)),
            ]),
            to,
        )
    }

    fn tell_trade(&mut self, key: &str) -> Result<(), VmError> {
        let Some(Value::Map(trade)) = self.trades.get(key).cloned() else {
            return Ok(());
        };
        let to = self.players_of(&ids_of(trade.get("between")));
        let get = |k: &str| trade.get(k).cloned().unwrap_or(Value::Null);
        self.tell(
            "trade",
            entry(vec![
                ("between", get("between")),
                ("offers", get("offers")),
                ("accepted", get("accepted")),
            ]),
            to,
        )
    }

    /// A hero leaving the world: out of its party, its trades cancelled.
    pub(super) fn part(&mut self, hero: &str) -> Result<(), VmError> {
        let in_party = match self.field_of(hero, "party") {
            Some(Value::Str(p)) if !p.is_empty() => self.parties.contains_key(p),
            _ => false,
        };
        if in_party {
            self.party_leave(hero)?;
        }
        let mut keys: Vec<String> = self
            .trades
            .iter()
            .filter(|(_, t)| match t {
                Value::Map(t) => ids_of(t.get("between")).iter().any(|e| e == hero),
                _ => false,
            })
            .map(|(k, _)| k.clone())
            .collect();
        keys.sort();
        for key in keys {
            let Some(Value::Map(trade)) = self.trades.get(&key).cloned() else {
                continue;
            };
            self.put(Root::Trades, &key, None);
            let others: Vec<String> = ids_of(trade.get("between"))
                .into_iter()
                .filter(|e| e != hero)
                .collect();
            let to = self.players_of(&others);
            self.tell(
                "trade",
                entry(vec![
                    (
                        "between",
                        trade.get("between").cloned().unwrap_or(Value::Null),
                    ),
                    ("cancelled", Value::Bool(true)),
                ]),
                to,
            )?;
        }
        Ok(())
    }
}

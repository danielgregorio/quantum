//! A world's ledger in the engine (ledger.py): its money and its things, made, moved and spent only by q:give, q:pay,
//! q:take and q:loot, and booked by asset and by where it happened. The quests' goals and rewards (together.py's)
//! are here too, since a quest's reward is the ledger's, and what the expressions read of both.

use super::*;

/// ledger.py's held of a currency: int() of a number (not a bool), else 0.
fn money_of(v: Option<&Value>) -> i64 {
    match v {
        Some(Value::Int(i)) => *i,
        Some(Value::Float(f)) => *f as i64,
        _ => 0,
    }
}

/// ledger.py's held of an item: int() of what the bag counts.
fn count_of(v: Option<&Value>) -> i64 {
    match v {
        Some(Value::Int(i)) => *i,
        Some(Value::Float(f)) => *f as i64,
        Some(Value::Bool(b)) => *b as i64,
        _ => 0,
    }
}

fn number(v: Option<&Value>) -> bool {
    matches!(v, Some(Value::Int(_) | Value::Float(_)))
}

/// A world's function's failure for a key Python's dict cannot hash.
fn unhashable(name: &str, v: &Value) -> Option<VmError> {
    matches!(v, Value::List(_) | Value::Map(_) | Value::Entity(_))
        .then(|| failed(name, format!("unhashable type: '{}'", vm::type_name_of(v))))
}

impl World {
    pub(super) fn first_currency(&self) -> Option<String> {
        self.def.currencies.keys().next().cloned()
    }

    /// What a holder holds of an asset (ledger.py's held).
    pub(super) fn held(&self, holder: &Map, asset: &str, money: bool) -> i64 {
        if money {
            return money_of(holder.get(asset));
        }
        match holder.get("bag") {
            Some(Value::Map(bag)) => count_of(bag.get(asset)),
            _ => 0,
        }
    }

    pub(super) fn held_by(&self, id: &str, asset: &str, money: bool) -> i64 {
        self.entity_map(id)
            .map_or(0, |h| self.held(h, asset, money))
    }

    /// (the asset, how many, is it a currency) of a give, a take or a pay.
    fn asset_of(
        &self,
        item: &Value,
        count: &Value,
        amount: &Value,
        currency: &Value,
        line: u32,
    ) -> Result<(String, i64, bool), VmError> {
        let no_item = matches!(item, Value::Null);
        if no_item == matches!(amount, Value::Null) {
            return Err(rule_at("an item= or an amount=, one of them", line));
        }
        let (asset, n) = if !no_item {
            let name = match item {
                Value::Str(s) if !s.is_empty() => s.clone(),
                _ => {
                    return Err(rule_at(
                        format!("item= is the name of an item, not {}", vm::py_repr(item)),
                        line,
                    ))
                }
            };
            if !self.def.items.is_empty() && !self.def.items.contains_key(&name) {
                let mut names: Vec<&str> = self.def.items.keys().map(String::as_str).collect();
                names.sort();
                return Err(rule_at(
                    format!(
                        "there is no item {} (the world has {})",
                        vm::str_repr(&name),
                        names.join(", ")
                    ),
                    line,
                ));
            }
            (name, count.clone())
        } else {
            let Some(first) = self.first_currency() else {
                return Err(rule_at(
                    "amount= is of a currency, and the world has no q:currency",
                    line,
                ));
            };
            let currency = match currency {
                Value::Str(s) if !s.is_empty() => s.clone(),
                _ => first,
            };
            if !self.def.currencies.contains_key(&currency) {
                return Err(rule_at(
                    format!("there is no currency {}", vm::str_repr(&currency)),
                    line,
                ));
            }
            (currency, amount.clone())
        };
        let n = match n {
            Value::Float(f) if f.is_finite() && f == f.trunc() => Value::Int(f as i64),
            n => n,
        };
        match n {
            Value::Int(n) if n >= 0 => {
                let money = self.def.currencies.contains_key(&asset);
                Ok((asset, n, money))
            }
            n => Err(rule_at(
                format!(
                    "{} is not a whole number of {asset} (0 or more)",
                    vm::py_repr(&n)
                ),
                line,
            )),
        }
    }

    /// n more (or fewer) of an asset to a holder's field (ledger.py's _move).
    pub(super) fn shift(
        &mut self,
        id: &str,
        asset: &str,
        n: i64,
        money: bool,
        line: u32,
    ) -> Result<(), VmError> {
        let (shown, fits, have) = match self.entity_map(id) {
            Some(h) => (
                h.get("id").map_or_else(|| "None".to_string(), vm::py_str),
                if money {
                    number(h.get(asset))
                } else {
                    matches!(h.get("bag"), Some(Value::Map(_)))
                },
                self.held(h, asset, money),
            ),
            None => ("None".to_string(), false, 0),
        };
        if money {
            if !fits {
                return Err(rule_at(
                    format!("{shown} holds no {asset} (a field of it that is a number)"),
                    line,
                ));
            }
            return self.write_field(id, asset, Value::Int(have + n), line);
        }
        if !fits {
            return Err(rule_at(
                format!("{shown} has no bag to hold {asset} (a field that is a record)"),
                line,
            ));
        }
        let left = have + n;
        if left != 0 {
            self.write(
                Root::Entity(id.to_string()),
                vec!["bag".into()],
                asset,
                &Value::Int(left),
                line,
            )
        } else {
            self.put_at(
                Root::Entity(id.to_string()),
                vec!["bag".into()],
                asset,
                None,
            );
            self.dirty.insert(id.to_string());
            Ok(())
        }
    }

    /// n of an asset made (kind "made") or spent ("spent") where the world is, in its books.
    fn book(&mut self, kind: &str, asset: &str, n: i64) {
        if n == 0 {
            return;
        }
        let book = match self.books.get(kind) {
            Some(Value::Map(b)) => b.get(asset),
            _ => None,
        };
        let had = match book {
            Some(Value::Map(a)) => Some(a.get(&self.source).and_then(Value::as_whole).unwrap_or(0)),
            _ => None,
        };
        if had.is_none() {
            self.put_at(
                Root::Books,
                vec![kind.to_string()],
                asset,
                Some(Value::Map(Map::default())),
            );
        }
        let source = self.source.clone();
        self.put_at(
            Root::Books,
            vec![kind.to_string(), asset.to_string()],
            &source,
            Some(Value::Int(had.unwrap_or(0) + n)),
        );
    }

    pub(super) fn give(
        &mut self,
        to: &str,
        item: &Value,
        count: &Value,
        amount: &Value,
        currency: &Value,
        line: u32,
    ) -> Result<(), VmError> {
        let (asset, n, money) = self.asset_of(item, count, amount, currency, line)?;
        self.shift(to, &asset, n, money, line)?;
        self.book("made", &asset, n);
        Ok(())
    }

    pub(super) fn take(
        &mut self,
        from: &str,
        item: &Value,
        count: &Value,
        amount: &Value,
        currency: &Value,
        line: u32,
    ) -> Result<(), VmError> {
        let (asset, n, money) = self.asset_of(item, count, amount, currency, line)?;
        if self.held_by(from, &asset, money) < n {
            return Err(refused(format!("Not enough {asset}.")));
        }
        self.shift(from, &asset, -n, money, line)?;
        self.book("spent", &asset, n);
        Ok(())
    }

    pub(super) fn pay(
        &mut self,
        payer: &str,
        to: &str,
        amount: &Value,
        currency: &Value,
        line: u32,
    ) -> Result<(), VmError> {
        let (asset, n, money) =
            self.asset_of(&Value::Null, &Value::Null, amount, currency, line)?;
        if self.held_by(payer, &asset, money) < n {
            return Err(refused(format!("Not enough {asset}.")));
        }
        self.shift(payer, &asset, -n, money, line)?;
        self.shift(to, &asset, n, money, line)
    }

    /// What a holder holds, by asset, in ledger.py's order (its currencies, then its bag).
    pub(super) fn holdings(&self, holder: &Map) -> Vec<(String, i64)> {
        if !self.def.ledger() {
            return Vec::new();
        }
        let mut out: IndexMap<String, i64> = IndexMap::default();
        for c in self.def.currencies.keys() {
            if holder.contains_key(c) {
                out.insert(c.clone(), self.held(holder, c, true));
            }
        }
        if let Some(Value::Map(bag)) = holder.get("bag") {
            for (item, n) in bag {
                *out.entry(item.clone()).or_insert(0) += count_of(Some(n));
            }
        }
        out.into_iter().filter(|(_, n)| *n != 0).collect()
    }

    fn book_all(&mut self, holder: &Map, kind: &str, where_: &str) {
        let before = std::mem::replace(&mut self.source, where_.to_string());
        for (asset, n) in self.holdings(holder) {
            self.book(kind, &asset, n);
        }
        self.source = before;
    }

    /// What a holder is made with, booked as made at its start.
    pub(super) fn mint_start(&mut self, holder: &Map) {
        self.book_all(holder, "made", "start");
    }

    /// A holder gone from the world for good: what it held, booked as spent there.
    pub(super) fn spend_all(&mut self, holder: &Map, where_: &str) {
        self.book_all(holder, "spent", where_);
    }

    /// q:loot in a world with a ledger: each drop made by it, booked as this kind's loot.
    pub(super) fn loot_booked(&mut self, of: &str, to: &str, line: u32) -> Result<(), VmError> {
        let kind = self
            .field_of(of, "kind")
            .map_or_else(|| "None".to_string(), vm::py_str);
        let spec = match self.field_of(of, "_type") {
            Some(Value::Str(t)) => self.def.entities.get(t).map(|_| t.clone()),
            _ => None,
        };
        let before = std::mem::replace(&mut self.source, format!("loot of {kind}"));
        let result = self.drops(spec.as_deref(), to, line);
        self.source = before;
        result
    }

    fn drops(&mut self, spec: Option<&str>, to: &str, line: u32) -> Result<(), VmError> {
        let Some(spec) = spec else {
            return Ok(());
        };
        let def = self.def.clone();
        for drop in def.entities[spec].loot.iter() {
            if self.rng.random() >= drop.chance {
                continue;
            }
            if let Some(item) = &drop.item {
                let n = self.rng.randint(drop.count.0, drop.count.1).unwrap_or(0);
                self.give(
                    to,
                    &Value::Str(item.clone()),
                    &Value::Int(n),
                    &Value::Null,
                    &Value::Null,
                    line,
                )?;
            } else {
                let (lo, hi) = drop.gold.unwrap_or((0, 0));
                let n = self.rng.randint(lo, hi).unwrap_or(0);
                self.give(
                    to,
                    &Value::Null,
                    &Value::Null,
                    &Value::Int(n),
                    &Value::Null,
                    line,
                )?;
            }
        }
        Ok(())
    }

    // -- the quests (together.py's) --------------------------------------------------------------------------------

    fn quest_of(&self, x: &Value) -> Option<&QuestDef> {
        let id = self.entity_from(x)?;
        let name = match self.field_of(&id, "quest") {
            Some(Value::Map(q)) => q.get("name"),
            _ => None,
        };
        match name {
            Some(Value::Str(n)) => self.def.quests.get(n),
            _ => None,
        }
    }

    /// q:reward: what a quest gives, and what it was brought for, taken.
    pub(super) fn reward(&mut self, to: &str, name: &Value, line: u32) -> Result<(), VmError> {
        let def = self.def.clone();
        let quest = match name {
            Value::Str(n) => def.quests.get(n),
            _ => None,
        };
        let Some(quest) = quest else {
            return Err(rule_at(
                format!("q:reward quest=: there is no quest {}", vm::py_repr(name)),
                line,
            ));
        };
        let (kind, what, count) = &quest.goal;
        if kind == "bring" {
            self.take(
                to,
                &Value::Str(what.clone()),
                &Value::Int(*count),
                &Value::Null,
                &Value::Null,
                line,
            )?;
        }
        for (key, n) in quest.reward.iter() {
            if def.currencies.contains_key(key) {
                self.give(
                    to,
                    &Value::Null,
                    &Value::Null,
                    &Value::Int(*n),
                    &Value::Str(key.clone()),
                    line,
                )?;
            } else if let Some(item) = key.strip_prefix("item:") {
                self.give(
                    to,
                    &Value::Str(item.to_string()),
                    &Value::Int(*n),
                    &Value::Null,
                    &Value::Null,
                    line,
                )?;
            } else {
                let current = self.field_of(to, key).cloned();
                match current {
                    Some(v @ (Value::Int(_) | Value::Float(_))) => {
                        let sum = python_add(v, *n)?;
                        self.write_field(to, key, sum, line)?;
                    }
                    _ => {
                        let shown = self
                            .field_of(to, "id")
                            .map_or_else(|| "None".to_string(), vm::py_str);
                        return Err(rule_at(
                            format!(
                                "q:reward {key}:{n}: {shown} has no field {key} that is a number"
                            ),
                            line,
                        ));
                    }
                }
            }
        }
        Ok(())
    }

    // -- what the expressions read of them ---------------------------------------------------------------------------

    fn item_value(
        &self,
        item: &Value,
        key: &Value,
        default: Value,
    ) -> Result<Value, Option<String>> {
        let props = match item {
            Value::Str(s) => self.def.items.get(s),
            _ => None,
        };
        match props {
            Some(p) if !p.is_empty() => match key {
                Value::Str(k) => Ok(p.get(k).cloned().unwrap_or(default)),
                Value::List(_) | Value::Map(_) | Value::Entity(_) => {
                    Err(Some(vm::type_name_of(key).to_string()))
                }
                _ => Ok(default),
            },
            _ => Ok(default),
        }
    }

    /// The ledger's and the quests' functions (rules.py's _functions): None for a name that is not one of them.
    pub(super) fn ledger_call(
        &mut self,
        name: &str,
        a: &[Value],
    ) -> Option<Result<Value, VmError>> {
        let arg = |i: usize| a.get(i).cloned().unwrap_or(Value::Null);
        let quest_key = |name: &str, q: &Value| -> Result<Option<&QuestDef>, VmError> {
            if let Some(e) = unhashable(name, q) {
                return Err(e);
            }
            Ok(match q {
                Value::Str(s) => self.def.quests.get(s),
                _ => None,
            })
        };
        Some(match name {
            "balance" => {
                let currency = arg(1);
                match self.entity_from(&arg(0)) {
                    None => Ok(Value::Int(0)),
                    Some(_) if self.def.currencies.is_empty() => Ok(Value::Int(0)),
                    Some(id) => {
                        let currency = if vm::truthy(&currency) {
                            currency
                        } else {
                            Value::Str(self.first_currency().unwrap_or_default())
                        };
                        if let Some(e) = unhashable("balance", &currency) {
                            return Some(Err(e));
                        }
                        Ok(Value::Int(match &currency {
                            Value::Str(c) => self.held_by(&id, c, true),
                            _ => 0,
                        }))
                    }
                }
            }
            "has" => match (self.entity_from(&arg(0)), arg(1)) {
                (Some(id), Value::Str(item)) => {
                    let n = if a.len() > 2 {
                        match self.whole("has", &arg(2)) {
                            Ok(n) => n,
                            Err(e) => return Some(Err(e)),
                        }
                    } else {
                        1
                    };
                    Ok(Value::Bool(self.held_by(&id, &item, false) >= n))
                }
                _ => Ok(Value::Bool(false)),
            },
            "item" => Ok(match &arg(0) {
                Value::Str(s) => self
                    .def
                    .items
                    .get(s)
                    .map_or(Value::Null, |p| Value::Map(p.clone())),
                _ => Value::Null,
            }),
            "price" | "heals" | "slot" => {
                let default = if name == "slot" {
                    Value::Str(String::new())
                } else {
                    Value::Int(0)
                };
                Ok(self
                    .item_value(&arg(0), &Value::Str(name.to_string()), default)
                    .unwrap_or_else(|_| Value::Null))
            }
            "bonus" => match self.item_value(&arg(0), &arg(1), Value::Int(0)) {
                Ok(v @ (Value::Int(_) | Value::Float(_) | Value::Bool(_))) => Ok(v),
                Ok(_) => Ok(Value::Int(0)),
                Err(t) => Err(failed(
                    "bonus",
                    format!("unhashable type: '{}'", t.unwrap_or_default()),
                )),
            },
            "quest_goal" => Ok(Value::Str(
                self.quest_of(&arg(0))
                    .map_or_else(String::new, |q| format!("{}:{}", q.goal.0, q.goal.1)),
            )),
            "quest_done" => {
                let x = arg(0);
                let Some(quest) = self.quest_of(&x) else {
                    return Some(Ok(Value::Bool(false)));
                };
                let (kind, what, n) = quest.goal.clone();
                if kind == "bring" {
                    let id = self.entity_from(&x).unwrap_or_default();
                    Ok(Value::Bool(self.held_by(&id, &what, false) >= n))
                } else {
                    let id = self.entity_from(&x).unwrap_or_default();
                    let done = match self.field_of(&id, "quest") {
                        Some(Value::Map(q)) => q.get("done").cloned().unwrap_or(Value::Int(0)),
                        _ => Value::Int(0),
                    };
                    Ok(Value::Bool(match done {
                        Value::Int(d) => d >= n,
                        Value::Bool(b) => (b as i64) >= n,
                        Value::Float(f) => f >= n as f64,
                        _ => false,
                    }))
                }
            }
            "quest_level" => {
                quest_key("quest_level", &arg(0)).map(|q| Value::Int(q.map_or(0, |q| q.level)))
            }
            "quest_title" => quest_key("quest_title", &arg(0))
                .map(|q| Value::Str(q.map_or_else(String::new, |q| q.title.clone()))),
            _ => return None,
        })
    }
}

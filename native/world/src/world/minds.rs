//! A world's NPCs with minds in the engine (npc.py's Minds). A player's q:ask gives an NPC their words; the tick does
//! not wait for its mind: the NPC is seen thinking, the question goes out with the tick (its asks), and the answer
//! comes back some ticks later as an input of the world, ('npc', account, npc id, answer). Its tools (commands with
//! by="npc") run as the player it talks to, whole or not at all; a mind with no answer, or a player out of the day's
//! budget, gets a line of its q:fallback, from the world's random.

use super::together::py_strip;
use super::*;

pub const MAX_WORDS: usize = 200;
pub const MAX_SAY: usize = 300;
pub const MAX_MEMORY: usize = 500;

/// Python's str.isprintable() of a character: not a control, a format character, a separator (but the space), a
/// private use or a noncharacter. (Unicode's unassigned code points, which Python also counts out, are counted in.)
fn printable(c: char) -> bool {
    if c == ' ' {
        return true;
    }
    if c.is_control() || c.is_whitespace() {
        return false;
    }
    let n = c as u32;
    let format = matches!(
        n,
        0xAD | 0x600..=0x605
            | 0x61C
            | 0x6DD
            | 0x70F
            | 0x890..=0x891
            | 0x8E2
            | 0x180E
            | 0x200B..=0x200F
            | 0x202A..=0x202E
            | 0x2060..=0x2064
            | 0x2066..=0x206F
            | 0xFEFF
            | 0xFFF9..=0xFFFB
            | 0x110BD
            | 0x110CD
            | 0x13430..=0x1343F
            | 0x1BCA0..=0x1BCA3
            | 0x1D173..=0x1D17A
            | 0xE0001
            | 0xE0020..=0xE007F
    );
    let private = matches!(n, 0xE000..=0xF8FF | 0xF0000..=0xFFFFD | 0x100000..=0x10FFFD);
    let nonchar = matches!(n, 0xFDD0..=0xFDEF) || (n & 0xFFFE) == 0xFFFE;
    !(format || private || nonchar)
}

/// npc.py's _clean: what is printable of a text, stripped, at most so many characters.
fn clean_words(text: &Value, most: usize) -> String {
    let s = if vm::truthy(text) {
        vm::py_str(text)
    } else {
        String::new()
    };
    let kept: String = s.chars().filter(|c| printable(*c)).collect();
    py_strip(&kept).chars().take(most).collect()
}

impl World {
    /// The world's day (its q:clock's, else 24 hours of ticks): a budget is a day's.
    fn day_number(&self) -> i64 {
        let day = match self.def.day_ticks {
            Some(d) if d != 0 => d,
            _ => 24 * 3600 * self.def.tick_rate,
        };
        self.tick.div_euclid(day.max(1))
    }

    /// What a hero has of an NPC's mind ({day, asked, memory}), made when it has none.
    fn mind_of(&mut self, hero: &str, npc: &str) -> Result<Map, VmError> {
        if !matches!(self.field_of(hero, "_minds"), Some(Value::Map(_))) {
            self.write_field(hero, "_minds", Value::Map(Map::default()), 0)?;
        }
        let has =
            matches!(self.field_of(hero, "_minds"), Some(Value::Map(m)) if m.contains_key(npc));
        if !has {
            self.put_at(
                Root::Entity(hero.to_string()),
                vec!["_minds".into()],
                npc,
                Some(entry(vec![
                    ("day", Value::Int(-1)),
                    ("asked", Value::Int(0)),
                    ("memory", Value::Str(String::new())),
                ])),
            );
        }
        Ok(match self.field_of(hero, "_minds") {
            Some(Value::Map(m)) => match m.get(npc) {
                Some(Value::Map(mind)) => mind.clone(),
                _ => Map::default(),
            },
            _ => Map::default(),
        })
    }

    fn put_mind(&mut self, hero: &str, npc: &str, key: &str, value: Value) {
        self.put_at(
            Root::Entity(hero.to_string()),
            vec!["_minds".into(), npc.to_string()],
            key,
            Some(value),
        );
    }

    /// The players who see where an entity is (and one more).
    fn near_accounts(&self, entity: &str, also: Option<&str>) -> Vec<String> {
        let tile = self.entity_tile(entity);
        let reach = self.def.reach;
        let mut out: Vec<String> = also.into_iter().map(String::from).collect();
        for (account, id) in self.players.iter() {
            let there = self.entity_tile(id);
            if let (Some(there), Some(tile)) = (there, tile) {
                if reach.is_none_or(|r| chebyshev(there, tile) <= r) {
                    out.push(account.clone());
                }
            }
        }
        out
    }

    fn title_of(&self, entity: &str, spec: &str) -> Value {
        match self.field_of(entity, "title") {
            Some(t) if vm::truthy(t) => t.clone(),
            _ => Value::Str(spec.to_string()),
        }
    }

    /// q:ask: a player's words to an NPC, its answer to come off the tick (or a fallback line now).
    pub(super) fn ask(
        &mut self,
        me: &Value,
        npc: &Value,
        text: &Value,
        line: u32,
    ) -> Result<(), VmError> {
        let Some(hero) = self.hero_of(me) else {
            return Err(rule_at(
                "q:ask is a player's words: me is a player's entity (in a q:command)",
                line,
            ));
        };
        let entity = self.entity_from(npc);
        let spec = entity
            .as_deref()
            .and_then(|e| match self.field_of(e, "_type") {
                Some(Value::Str(t)) if self.def.npcs.contains_key(t) => Some(t.clone()),
                _ => None,
            });
        let (Some(entity), Some(spec)) = (entity, spec) else {
            return Err(rule_at(
                format!(
                    "q:ask npc=: {} is not an NPC of the world (a q:npc)",
                    vm::py_repr(npc)
                ),
                line,
            ));
        };
        let words = clean_words(text, MAX_WORDS);
        if words.is_empty() {
            return Err(refused("Say something."));
        }
        let def = self.def.clone();
        let npc_def = &def.npcs[&spec];
        let mind = self.mind_of(&hero, &npc_def.name)?;
        let today = self.day_number();
        let mut asked = mind.get("asked").and_then(Value::as_whole).unwrap_or(0);
        if !mind
            .get("day")
            .is_some_and(|d| py_eq(d, &Value::Int(today)))
        {
            self.put_mind(&hero, &npc_def.name, "day", Value::Int(today));
            self.put_mind(&hero, &npc_def.name, "asked", Value::Int(0));
            asked = 0;
        }
        let account = self.player_of(&hero).unwrap_or_default();
        if asked >= npc_def.budget {
            return self.fallback(&account, &entity, npc_def);
        }
        self.put_mind(&hero, &npc_def.name, "asked", Value::Int(asked + 1));
        let title = self.title_of(&entity, &npc_def.name);
        let near = self.near_accounts(&entity, Some(&account));
        self.tell(
            "npc-thinking",
            entry(vec![
                ("npc", Value::Str(entity.clone())),
                ("who", title.clone()),
            ]),
            near,
        )?;
        let player: Map = match self.entity_map(&hero) {
            Some(h) => h
                .iter()
                .filter(|(k, _)| !k.starts_with('_') && *k != "quest")
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect(),
            None => Map::default(),
        };
        let memory = if npc_def.memory {
            mind.get("memory")
                .cloned()
                .unwrap_or(Value::Str(String::new()))
        } else {
            Value::Str(String::new())
        };
        let knowledge = def
            .knowledge
            .get(npc_def.knowledge.as_deref().unwrap_or(""))
            .cloned()
            .unwrap_or_default();
        let tools: Vec<Value> = npc_def
            .tools
            .iter()
            .map(|(t, d)| {
                let params = def
                    .commands
                    .get(t)
                    .map(|c| c.params.iter().cloned().map(Value::Str).collect())
                    .unwrap_or_default();
                entry(vec![
                    ("name", Value::Str(t.clone())),
                    ("description", Value::Str(d.clone())),
                    ("params", Value::List(params)),
                ])
            })
            .collect();
        let ask = entry(vec![
            ("account", Value::Str(account)),
            ("npc", Value::Str(entity)),
            ("name", Value::Str(npc_def.name.clone())),
            ("title", title),
            ("model", Value::Str(npc_def.model.clone())),
            ("instruction", Value::Str(npc_def.instruction.clone())),
            ("knowledge", Value::Str(knowledge)),
            ("memory", memory),
            ("player", Value::Map(player)),
            ("text", Value::Str(words)),
            ("tools", Value::List(tools)),
            ("max_tools", Value::Int(npc_def.max_tools)),
        ]);
        let ask = self.plain(&ask, 0).map_err(|m| rule_at(m, line))?;
        self.asks.push(ask);
        Ok(())
    }

    /// A line of the NPC's q:fallback, from the world's random.
    fn fallback(&mut self, account: &str, entity: &str, spec: &NpcDef) -> Result<(), VmError> {
        let i = if spec.lines.len() > 1 {
            self.rng.randrange(spec.lines.len() as i64).unwrap_or(0) as usize
        } else {
            0
        };
        let line = spec.lines.get(i).cloned().unwrap_or_default();
        let near = self.near_accounts(entity, Some(account));
        self.tell(
            "npc-says",
            entry(vec![
                ("npc", Value::Str(entity.to_string())),
                ("who", self.title_of(entity, &spec.name)),
                ("text", Value::Str(line)),
                ("did", Value::List(vec![])),
            ]),
            near,
        )
    }

    /// An NPC's answer, come back as an input of the tick: its tools run, its words said, its note kept.
    pub(super) fn answer(
        &mut self,
        account: &str,
        npc: &Value,
        answer: &Value,
    ) -> Result<(), Raised> {
        let hero = self.hero_of(&Value::Str(account.to_string()));
        let entity = match npc {
            Value::Str(id) if self.entities.contains_key(id) => Some(id.clone()),
            _ => None,
        };
        let spec = entity
            .as_deref()
            .and_then(|e| match self.field_of(e, "_type") {
                Some(Value::Str(t)) if self.def.npcs.contains_key(t) => Some(t.clone()),
                _ => None,
            });
        let (Some(hero), Some(entity), Some(spec)) = (hero, entity, spec) else {
            return Ok(());
        };
        let def = self.def.clone();
        let npc_def = &def.npcs[&spec];
        let said = match answer {
            Value::Map(a) if !a.get("fallback").is_some_and(vm::truthy) => match a.get("say") {
                Some(Value::Str(s)) => Some((s.clone(), a.clone())),
                _ => None,
            },
            _ => None,
        };
        let Some((say, answer)) = said else {
            return self.fallback(account, &entity, npc_def).map_err(Raised::of);
        };
        let mut did = Vec::new();
        let calls = match answer.get("do") {
            Some(Value::List(c)) => c.clone(),
            _ => Vec::new(),
        };
        for call in calls.iter().take(npc_def.max_tools.max(0) as usize) {
            let Value::Map(call) = call else {
                continue;
            };
            let tool = match call.get("tool") {
                Some(Value::Str(t)) if npc_def.tools.contains_key(t) => t.clone(),
                _ => continue,
            };
            let args = match call.get("args") {
                Some(Value::Map(a)) => a.clone(),
                _ => Map::default(),
            };
            if self.tool(account, &tool, args, &entity)? {
                did.push(Value::Str(tool));
            }
        }
        if npc_def.memory {
            if let Some(remember) = answer
                .get("remember")
                .filter(|r| matches!(r, Value::Str(_)))
            {
                self.source = format!("mind of {}", npc_def.name);
                self.begin();
                self.mind_of(&hero, &npc_def.name).map_err(Raised::of)?;
                let note = clean_words(remember, MAX_MEMORY);
                self.put_mind(&hero, &npc_def.name, "memory", Value::Str(note));
                self.commit();
            }
        }
        let text = clean_words(&Value::Str(say), MAX_SAY);
        let text = if text.is_empty() {
            "...".to_string()
        } else {
            text
        };
        let near = self.near_accounts(&entity, Some(account));
        self.tell(
            "npc-says",
            entry(vec![
                ("npc", Value::Str(entity.clone())),
                ("who", self.title_of(&entity, &npc_def.name)),
                ("text", Value::Str(text)),
                ("did", Value::List(did)),
            ]),
            near,
        )
        .map_err(Raised::of)
    }

    /// A tool of an NPC run: its command, as the player it talks to (me), the NPC being npc; whole or not at all.
    fn tool(&mut self, account: &str, name: &str, args: Map, npc: &str) -> Result<bool, Raised> {
        let def = self.def.clone();
        let Some(command) = def.commands.get(name) else {
            return Ok(false);
        };
        let hero = self.hero_of(&Value::Str(account.to_string()));
        let given: HashSet<&String> = args.keys().collect();
        let wanted: HashSet<&String> = command.params.iter().collect();
        let args = Value::Map(args.clone());
        let mut text = String::new();
        dumps(&args, false, &mut text);
        if given != wanted || !args_ok(&args, 0) || text.chars().count() > MAX_ARGS {
            return Ok(false);
        }
        let Some(body) = command.body.clone() else {
            return Ok(false);
        };
        self.source = format!("q:tool {name}");
        self.begin();
        let mut locals = Locals::default();
        locals.insert("me".into(), hero.map_or(Value::Null, Value::Entity));
        locals.insert("npc".into(), Value::Entity(npc.to_string()));
        if let Value::Map(m) = &args {
            for (k, v) in m {
                locals.insert(k.clone(), v.clone());
            }
        }
        match self.evaluate(&body, locals) {
            Ok(_) => {
                self.commit();
                Ok(true)
            }
            Err(e) => match Raised::of(e) {
                Raised::Refused(_) => {
                    self.rollback();
                    Ok(false)
                }
                Raised::Rule(message, line) => {
                    self.rollback();
                    self.error(&format!("q:tool {name}"), &message, line);
                    Ok(false)
                }
                python => Err(python),
            },
        }
    }
}

//! Inference engine abstraction for SLM execution.
//!
//! Backends, chosen by `SynapseConfig::backend`:
//! - `candle` (production, the default): a quantized GGUF model (Qwen2.5
//!   0.5B Instruct) run locally on the CPU with candle, pure Rust. The model
//!   and its tokenizer ship in the image under /var/lib/hive/models; without
//!   them the engine says so and falls back to the mock.
//! - `mock`: canned responses, for development and tests.
//! - `ollama` (dev/test only): calls a remote Ollama server's HTTP API,
//!   selected via `SynapseConfig::backend = "ollama"`. This exists to
//!   exercise the rest of the Hive Stack against real model output during
//!   development, using homelab hardware (e.g. a Mac mini running Ollama)
//!   that isn't part of a DruidOS deployment. It's never the default and
//!   production images shouldn't enable the `ollama` Cargo feature at
//!   all — but even if `backend = "ollama"` ended up in a real deployment
//!   by mistake, `config/systemd/hive-synapse.service`'s
//!   `PrivateNetwork=yes` isolates hive-synapse into its own network
//!   namespace at the OS level, so the outbound call simply fails rather
//!   than reaching anything. See CLAUDE.md's security rule: hive-synapse
//!   must never have network access in production.

use anyhow::{Context, Result};
use hive_common::config::SynapseConfig;
use std::path::PathBuf;
use tracing::{debug, info, warn};

/// Where the production model and its tokenizer live by default.
const DEFAULT_MODEL_PATH: &str = "/var/lib/hive/models/qwen2.5-0.5b-instruct-q4_k_m.gguf";
const DEFAULT_TOKENIZER_PATH: &str = "/var/lib/hive/models/qwen2.5-0.5b-instruct-tokenizer.json";

/// Which backend actually answers `generate()` calls.
enum Backend {
    Mock,
    #[cfg(feature = "candle")]
    Candle(std::sync::Arc<CandleState>),
    #[cfg(feature = "ollama")]
    Ollama {
        client: reqwest::Client,
        url: String,
        model: String,
    },
}

/// Inference engine that wraps the actual LLM backend
pub struct InferenceEngine {
    config: SynapseConfig,
    backend: Backend,
}

impl InferenceEngine {
    /// Create a new inference engine with the given configuration
    pub async fn new(config: &SynapseConfig) -> Result<Self> {
        let backend = match config.backend.as_str() {
            "candle" => Self::candle_backend(config).await?,
            "ollama" => Self::ollama_backend(config),
            "mock" => Backend::Mock,
            other => {
                warn!("Unknown inference backend {:?}, using mock", other);
                Backend::Mock
            }
        };

        Ok(Self {
            config: config.clone(),
            backend,
        })
    }

    #[cfg(feature = "candle")]
    async fn candle_backend(config: &SynapseConfig) -> Result<Backend> {
        let model_path = config
            .model_path
            .clone()
            .unwrap_or_else(|| PathBuf::from(DEFAULT_MODEL_PATH));
        let tokenizer_path = config
            .tokenizer_path
            .clone()
            .unwrap_or_else(|| PathBuf::from(DEFAULT_TOKENIZER_PATH));

        for (what, path) in [("Model", &model_path), ("Tokenizer", &tokenizer_path)] {
            if !path.exists() {
                warn!(
                    "{} not found at {}; using mock inference instead of the local model",
                    what,
                    path.display()
                );
                return Ok(Backend::Mock);
            }
        }

        let state = std::sync::Arc::new(CandleState {
            model_path,
            tokenizer_path,
            settings: candle_backend::Settings {
                max_tokens: config.max_tokens as usize,
                context_size: config.context_size as usize,
                temperature: config.temperature as f64,
                // The prompt asks for at most 3 suggestions.
                max_suggestion_lines: Some(3),
            },
            model: std::sync::Mutex::new(None),
        });

        if config.preload {
            let loading = state.clone();
            tokio::task::spawn_blocking(move || loading.ensure_loaded().map(|_| ()))
                .await
                .context("model loading task failed")??;
        } else {
            info!(
                "Local model {} will be loaded on the first request (preload = false)",
                state.model_path.display()
            );
        }
        Ok(Backend::Candle(state))
    }

    #[cfg(not(feature = "candle"))]
    async fn candle_backend(_config: &SynapseConfig) -> Result<Backend> {
        warn!("backend = \"candle\" but hive-synapse wasn't built with the `candle` feature — using mock");
        Ok(Backend::Mock)
    }

    fn ollama_backend(config: &SynapseConfig) -> Backend {
        #[cfg(feature = "ollama")]
        {
            let url = config
                .ollama_url
                .clone()
                .unwrap_or_else(|| "http://127.0.0.1:11434".to_string());
            let model = config
                .ollama_model
                .clone()
                .unwrap_or_else(|| "qwen2.5:7b".to_string());
            info!(
                "Using Ollama backend at {} (model {}) — dev/test only, see inference.rs docs",
                url, model
            );
            Backend::Ollama {
                client: reqwest::Client::new(),
                url,
                model,
            }
        }
        #[cfg(not(feature = "ollama"))]
        {
            let _ = config;
            warn!(
                "backend = \"ollama\" configured but hive-synapse wasn't built with \
                 the `ollama` feature — falling back to mock"
            );
            Backend::Mock
        }
    }

    /// Generate a response to a prompt made of a system part (who the
    /// assistant is) and a user part (the situation and the task).
    pub async fn generate(&self, system: &str, user: &str) -> Result<String> {
        debug!("Generating response for prompt ({} chars)", user.len());

        let response = match &self.backend {
            // The mock keys off the situation, not the (fixed) system text.
            Backend::Mock => self.mock_generate(user)?,
            #[cfg(feature = "candle")]
            Backend::Candle(state) => {
                let state = state.clone();
                let (system, user) = (system.to_string(), user.to_string());
                tokio::task::spawn_blocking(move || state.generate(&system, &user))
                    .await
                    .context("inference task failed")??
            }
            #[cfg(feature = "ollama")]
            Backend::Ollama { client, url, model } => {
                let prompt = format!("{system}\n\n{user}");
                Self::ollama_generate(client, url, model, &prompt).await?
            }
        };

        debug!("Generated response ({} chars)", response.len());
        Ok(response)
    }

    #[cfg(feature = "ollama")]
    async fn ollama_generate(
        client: &reqwest::Client,
        url: &str,
        model: &str,
        prompt: &str,
    ) -> Result<String> {
        let body = serde_json::json!({
            "model": model,
            "prompt": prompt,
            "stream": false,
        });

        let bytes = client
            .post(format!("{}/api/generate", url.trim_end_matches('/')))
            .json(&body)
            .send()
            .await
            .context("Failed to reach Ollama backend")?
            .error_for_status()
            .context("Ollama returned an error status")?
            .bytes()
            .await
            .context("Failed to read Ollama response body")?;

        parse_ollama_response(&bytes)
    }

    /// Mock generation for development/testing
    fn mock_generate(&self, prompt: &str) -> Result<String> {
        let prompt_lower = prompt.to_lowercase();

        // Analyze prompt and generate contextual mock responses
        // describe_trigger says a port is "already held by" its holder
        let port_conflict = prompt_lower.contains("port")
            && (prompt_lower.contains("conflict") || prompt_lower.contains("already held by"));
        let text = if port_conflict {
            self.suggest_port_conflict()
        } else if prompt_lower.contains("error") || prompt_lower.contains("failed") {
            self.suggest_error_recovery()
        } else if prompt_lower.contains("rm -rf") || prompt_lower.contains("dangerous") {
            self.suggest_dangerous_command()
        } else if prompt_lower.contains("install") {
            self.suggest_package_install()
        } else if prompt_lower.contains("disk") && prompt_lower.contains("space") {
            self.suggest_disk_space()
        } else {
            self.suggest_general()
        };
        Ok(fill_mock_names(&text, prompt))
    }

    fn suggest_port_conflict(&self) -> String {
        r#"Based on the port conflict detected:

- Check which process is using the port with `lsof -i :PORT`
- Consider using a different port for your application
- If the existing service isn't needed, stop it with `systemctl stop SERVICE`
- You can also use `ss -tlnp` to see all listening ports"#
            .to_string()
    }

    fn suggest_error_recovery(&self) -> String {
        r#"To help resolve this error:

- Check the service logs with `journalctl -u SERVICE -n 50`
- Verify configuration files are valid
- Try restarting the service with `systemctl restart SERVICE`
- Check for missing dependencies"#
            .to_string()
    }

    fn suggest_dangerous_command(&self) -> String {
        r#"Warning: This command could be destructive.

- Consider using `trash-cli` instead of `rm` for recoverable deletion
- Double-check the path before proceeding
- Use `rm -i` for interactive confirmation"#
            .to_string()
    }

    fn suggest_package_install(&self) -> String {
        r#"For this package installation:

- Check package info with `apt show PACKAGE`
- Review what will be installed with `apt install --dry-run PACKAGE`
- Consider checking for alternatives with `apt search KEYWORD`"#
            .to_string()
    }

    fn suggest_disk_space(&self) -> String {
        r#"To free up disk space:

- Remove old packages: `apt autoremove`
- Clean package cache: `apt clean`
- Find large files: `du -h --max-depth=1 / | sort -hr | head -20`
- Check for old kernels: `dpkg -l 'linux-*' | grep ^ii`
- Remove old snapshots if using ZFS"#
            .to_string()
    }

    fn suggest_general(&self) -> String {
        r#"I'm here to help. Based on the current context:

- Check system status with `systemctl status`
- View recent logs with `journalctl -n 50`
- Monitor resources with `htop` or `top`"#
            .to_string()
    }

    /// Get the maximum context size in tokens
    #[allow(dead_code)]
    pub fn context_size(&self) -> usize {
        self.config.context_size as usize
    }

    /// Get the maximum output tokens
    #[allow(dead_code)]
    pub fn max_tokens(&self) -> usize {
        self.config.max_tokens as usize
    }
}

/// The names a mock suggestion leaves as PACKAGE, SERVICE, PORT and KEYWORD,
/// filled in from the event the prompt describes (`prompt::describe_trigger`
/// writes it). A line whose name the prompt does not give is left out: a
/// user must never be told to run `apt show PACKAGE`.
fn fill_mock_names(text: &str, prompt: &str) -> String {
    fn between<'a>(text: &'a str, start: &str, end: &str) -> Option<&'a str> {
        let rest = &text[text.find(start)? + start.len()..];
        Some(&rest[..rest.find(end)?])
    }
    let logging = prompt
        .find(" is logging an unusual number of errors")
        .map(|end| {
            let start = prompt[..end].rfind('\n').map_or(0, |i| i + 1);
            &prompt[start..end]
        });
    let service = between(prompt, "The service ", " crashed")
        .or(logging)
        .map(|s| s.trim().trim_end_matches(".service"));
    let port = between(prompt, "listening on port ", ":");
    let package = between(prompt, "; the ", " package provides it");
    let command = between(prompt, "A user tried to run `", "`");
    let names = [
        ("PACKAGE", package),
        ("SERVICE", service),
        ("PORT", port),
        ("KEYWORD", command),
    ];
    text.lines()
        .filter_map(|line| {
            let mut line = line.to_string();
            for (placeholder, value) in names {
                if line.contains(placeholder) {
                    line = line.replace(placeholder, value?);
                }
            }
            Some(line)
        })
        .collect::<Vec<_>>()
        .join("\n")
}

/// The local model, loaded on first use, shared with blocking tasks.
#[cfg(feature = "candle")]
struct CandleState {
    model_path: PathBuf,
    tokenizer_path: PathBuf,
    settings: candle_backend::Settings,
    model: std::sync::Mutex<Option<candle_backend::QwenModel>>,
}

#[cfg(feature = "candle")]
impl CandleState {
    fn ensure_loaded(
        &self,
    ) -> Result<std::sync::MutexGuard<'_, Option<candle_backend::QwenModel>>> {
        let mut model = self
            .model
            .lock()
            .map_err(|_| anyhow::anyhow!("model lock poisoned"))?;
        if model.is_none() {
            let started = std::time::Instant::now();
            *model = Some(candle_backend::QwenModel::load(
                &self.model_path,
                &self.tokenizer_path,
            )?);
            info!(
                "Loaded local model {} with candle in {} ms",
                self.model_path.display(),
                started.elapsed().as_millis()
            );
        }
        Ok(model)
    }

    fn generate(&self, system: &str, user: &str) -> Result<String> {
        let mut model = self.ensure_loaded()?;
        let model = model.as_mut().expect("loaded above");
        let seed = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_nanos() as u64);

        let started = std::time::Instant::now();
        let generation = model.generate(system, user, &self.settings, seed)?;
        let elapsed = started.elapsed();
        info!(
            "Generated {} tokens in {} ms with candle ({:.1} tokens/s, prompt {} tokens)",
            generation.generated_tokens,
            elapsed.as_millis(),
            generation.generated_tokens as f64 / elapsed.as_secs_f64().max(1e-9),
            generation.prompt_tokens
        );
        Ok(generation.text)
    }
}

/// Extracts the generated text out of an Ollama `/api/generate` response
/// body (`stream: false`, so it's a single JSON object with a `response`
/// field). Kept as a plain function — independent of the `ollama` Cargo
/// feature and the network client — so it's testable without a real
/// server. Its only real caller (`ollama_generate`) is behind
/// `#[cfg(feature = "ollama")]`, so in a default build this is only
/// reachable from tests.
#[allow(dead_code)]
fn parse_ollama_response(bytes: &[u8]) -> Result<String> {
    #[derive(serde::Deserialize)]
    struct OllamaGenerateResponse {
        response: String,
    }

    let parsed: OllamaGenerateResponse = serde_json::from_slice(bytes).with_context(|| {
        format!(
            "Malformed Ollama response: {}",
            String::from_utf8_lossy(bytes)
        )
    })?;
    Ok(parsed.response)
}

#[cfg(feature = "candle")]
pub mod candle_backend {
    //! Local inference with candle (pure Rust) on a quantized Qwen2 GGUF.

    use anyhow::{ensure, Context, Result};
    use candle_core::quantized::gguf_file;
    use candle_core::{Device, Tensor};
    use candle_transformers::generation::{LogitsProcessor, Sampling};
    use candle_transformers::models::quantized_qwen2::ModelWeights;
    use std::path::Path;
    use tokenizers::Tokenizer;

    /// Repetition penalty over the most recent tokens: small models loop
    /// ("- Check the logs\n- Check the logs\n...") without one.
    const REPEAT_PENALTY: f32 = 1.1;
    const REPEAT_WINDOW: usize = 64;

    pub struct Settings {
        pub max_tokens: usize,
        pub context_size: usize,
        pub temperature: f64,
        /// Stop after this many complete "- " lines, if set.
        pub max_suggestion_lines: Option<usize>,
    }

    /// Finished (newline-terminated) lines that start a suggestion.
    pub fn complete_suggestion_lines(text: &str) -> usize {
        let finished = match text.rfind('\n') {
            Some(end) => &text[..end],
            None => return 0,
        };
        finished
            .lines()
            .filter(|line| {
                let line = line.trim_start();
                line.starts_with("- ") || line.starts_with("* ")
            })
            .count()
    }

    pub struct Generation {
        pub text: String,
        pub prompt_tokens: usize,
        pub generated_tokens: usize,
    }

    pub struct QwenModel {
        weights: ModelWeights,
        tokenizer: Tokenizer,
        device: Device,
        stop_tokens: Vec<u32>,
    }

    impl QwenModel {
        pub fn load(model: &Path, tokenizer: &Path) -> Result<Self> {
            let device = Device::Cpu;
            let mut file = std::fs::File::open(model)
                .with_context(|| format!("opening model {}", model.display()))?;
            let content = gguf_file::Content::read(&mut file)
                .with_context(|| format!("reading GGUF {}", model.display()))?;
            let weights = ModelWeights::from_gguf(content, &mut file, &device)
                .with_context(|| format!("loading Qwen2 weights from {}", model.display()))?;
            let tokenizer = Tokenizer::from_file(tokenizer)
                .map_err(|e| anyhow::anyhow!("loading tokenizer {}: {e}", tokenizer.display()))?;

            let stop_tokens: Vec<u32> = ["<|im_end|>", "<|endoftext|>"]
                .iter()
                .filter_map(|token| tokenizer.token_to_id(token))
                .collect();
            ensure!(
                !stop_tokens.is_empty(),
                "tokenizer has no Qwen end-of-turn token"
            );

            Ok(Self {
                weights,
                tokenizer,
                device,
                stop_tokens,
            })
        }

        pub fn generate(
            &mut self,
            system: &str,
            user: &str,
            settings: &Settings,
            seed: u64,
        ) -> Result<Generation> {
            let encoding = self
                .tokenizer
                .encode(chat_prompt(system, user), false)
                .map_err(|e| anyhow::anyhow!("tokenizing prompt: {e}"))?;
            let mut prompt: Vec<u32> = encoding.get_ids().to_vec();
            // Keep the end of an over-long prompt (the task and the
            // assistant turn) and leave room for the answer.
            let budget = settings
                .context_size
                .saturating_sub(settings.max_tokens)
                .max(1);
            if prompt.len() > budget {
                prompt.drain(..prompt.len() - budget);
            }

            let sampling = if settings.temperature <= 0.0 {
                Sampling::ArgMax
            } else {
                Sampling::TopKThenTopP {
                    k: 40,
                    p: 0.9,
                    temperature: settings.temperature,
                }
            };
            let mut sampler = LogitsProcessor::from_sampling(seed, sampling);

            let mut generated: Vec<u32> = Vec::new();
            let mut input = Tensor::new(prompt.as_slice(), &self.device)?.unsqueeze(0)?;
            let mut position = 0;
            for _ in 0..settings.max_tokens {
                // index_pos 0 starts a fresh KV cache for this generation.
                let logits = self.weights.forward(&input, position)?.squeeze(0)?;
                position += input.dim(1)?;

                let recent: Vec<u32> = prompt
                    .iter()
                    .chain(&generated)
                    .rev()
                    .take(REPEAT_WINDOW)
                    .copied()
                    .collect();
                let logits = candle_transformers::utils::apply_repeat_penalty(
                    &logits,
                    REPEAT_PENALTY,
                    &recent,
                )?;
                let next = sampler.sample(&logits)?;
                if self.stop_tokens.contains(&next) {
                    break;
                }
                generated.push(next);

                // Small models ignore "at most N": stop once that many
                // suggestion lines are complete instead of spending seconds
                // on ones that would be cut anyway.
                if let Some(limit) = settings.max_suggestion_lines {
                    let piece = self.tokenizer.decode(&[next], true).unwrap_or_default();
                    if piece.contains('\n') {
                        let text = self.tokenizer.decode(&generated, true).unwrap_or_default();
                        if complete_suggestion_lines(&text) >= limit {
                            break;
                        }
                    }
                }
                input = Tensor::new(&[next], &self.device)?.unsqueeze(0)?;
            }

            let text = self
                .tokenizer
                .decode(&generated, true)
                .map_err(|e| anyhow::anyhow!("decoding output: {e}"))?;
            Ok(Generation {
                text,
                prompt_tokens: prompt.len(),
                generated_tokens: generated.len(),
            })
        }
    }

    /// Qwen2.5 Instruct's ChatML template, ready for the assistant's turn.
    pub fn chat_prompt(system: &str, user: &str) -> String {
        format!(
            "<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"
        )
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn only_finished_suggestion_lines_count() {
            assert_eq!(complete_suggestion_lines("Here you go:\n- one\n- tw"), 1);
            assert_eq!(complete_suggestion_lines("- one\n* two\nnot one\n"), 2);
            assert_eq!(complete_suggestion_lines("- still typing"), 0);
        }

        #[test]
        fn chat_prompt_uses_chatml_and_opens_the_assistant_turn() {
            assert_eq!(
                chat_prompt("You are the Hive.", "nginx crashed."),
                "<|im_start|>system\nYou are the Hive.<|im_end|>\n\
                 <|im_start|>user\nnginx crashed.<|im_end|>\n\
                 <|im_start|>assistant\n"
            );
        }

        /// Runs the real model when HIVE_TEST_MODEL_DIR points at a directory
        /// holding the production GGUF and tokenizer (e.g. the ISO lab's
        /// model cache on Forge); skipped otherwise, since CI doesn't carry
        /// a 491 MB model.
        #[test]
        #[ignore = "needs the real model: set HIVE_TEST_MODEL_DIR"]
        fn real_model_answers_with_suggestions() {
            let dir = std::path::PathBuf::from(
                std::env::var("HIVE_TEST_MODEL_DIR").expect("HIVE_TEST_MODEL_DIR"),
            );
            let started = std::time::Instant::now();
            let mut model = QwenModel::load(
                &dir.join("qwen2.5-0.5b-instruct-q4_k_m.gguf"),
                &dir.join("qwen2.5-0.5b-instruct-tokenizer.json"),
            )
            .unwrap();
            eprintln!("load: {:?}", started.elapsed());

            let settings = Settings {
                max_tokens: 128,
                context_size: 2048,
                temperature: 0.3,
                max_suggestion_lines: Some(3),
            };
            let started = std::time::Instant::now();
            let generation = model
                .generate(
                    "You are the Hive, an assistant built into a Linux system.",
                    "The service nginx.service crashed with exit code 1. \
                     Reply with at most 3 short suggestions, one per line, each starting with \"- \".",
                    &settings,
                    42,
                )
                .unwrap();
            let elapsed = started.elapsed();
            eprintln!(
                "{} prompt tokens, {} generated in {:?} ({:.1} tokens/s):\n{}",
                generation.prompt_tokens,
                generation.generated_tokens,
                elapsed,
                generation.generated_tokens as f64 / elapsed.as_secs_f64(),
                generation.text
            );
            assert!(generation.generated_tokens > 0);
            assert!(generation.text.contains("- "), "{}", generation.text);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use hive_common::messages::HiveMessage;

    #[tokio::test]
    async fn test_mock_generation() {
        let config = SynapseConfig {
            backend: "mock".to_string(),
            ..Default::default()
        };
        let engine = InferenceEngine::new(&config).await.unwrap();

        let response = engine
            .generate("You are the Hive.", "There is a port conflict on port 8080")
            .await
            .unwrap();
        assert!(response.contains("port") || response.contains("lsof"));
    }

    #[tokio::test]
    async fn the_mock_names_what_the_event_names_and_leaves_out_what_it_does_not() {
        let config = SynapseConfig {
            backend: "mock".to_string(),
            ..Default::default()
        };
        let engine = InferenceEngine::new(&config).await.unwrap();
        let ask = |trigger: HiveMessage| {
            let engine = &engine;
            async move {
                let prompt = crate::prompt::describe_trigger(&trigger);
                engine.generate("You are the Hive.", &prompt).await.unwrap()
            }
        };
        let install = ask(HiveMessage::CommandNotFound {
            command: "htop".into(),
            package: "htop".into(),
        })
        .await;
        assert!(install.contains("`apt show htop`"), "{install}");
        assert!(install.contains("`apt search htop`"), "{install}");
        let conflict = ask(HiveMessage::PortConflict {
            port: 8080,
            requested_by: process("app"),
            held_by: process("nginx"),
        })
        .await;
        assert!(conflict.contains("`lsof -i :8080`"), "{conflict}");
        // nothing to name the service with: that line goes, the others stay
        assert!(
            !conflict.contains("SERVICE") && conflict.contains("`ss -tlnp`"),
            "{conflict}"
        );
        for text in [install, conflict] {
            for placeholder in ["PACKAGE", "SERVICE", "PORT", "KEYWORD"] {
                assert!(!text.contains(placeholder), "{placeholder} left in: {text}");
            }
        }
    }

    #[tokio::test]
    async fn the_mock_never_says_something_was_done_that_was_not() {
        // Found in the VM lab: after `rm -rf /srv`, the dashboard said "A ZFS
        // snapshot has been created for safety", on a system without ZFS.
        // Nothing takes a snapshot when a command is observed.
        let config = SynapseConfig {
            backend: "mock".to_string(),
            ..Default::default()
        };
        let engine = InferenceEngine::new(&config).await.unwrap();
        let prompt = crate::prompt::describe_trigger(&HiveMessage::CommandObserved {
            process: process("rm"),
            cmd: "rm -rf /srv".into(),
            timestamp: chrono::Utc::now(),
        });
        let text = engine.generate("You are the Hive.", &prompt).await.unwrap();
        assert!(
            text.contains("trash-cli"),
            "the dangerous command advice: {text}"
        );
        assert!(
            !text.contains("has been"),
            "claims something was done: {text}"
        );
    }

    fn process(name: &str) -> hive_common::messages::ProcessInfo {
        hive_common::messages::ProcessInfo {
            pid: 1,
            uid: 0,
            name: name.into(),
            cmdline: vec![name.into()],
            cwd: None,
            ppid: None,
        }
    }

    #[tokio::test]
    async fn unknown_backend_falls_back_to_mock() {
        let config = SynapseConfig {
            backend: "some-future-backend-nobody-wrote-yet".to_string(),
            ..Default::default()
        };
        let engine = InferenceEngine::new(&config).await.unwrap();
        assert!(matches!(engine.backend, Backend::Mock));
    }

    #[tokio::test]
    async fn the_local_model_falls_back_to_mock_when_its_files_are_missing() {
        let dir = tempfile::tempdir().unwrap();
        let config = SynapseConfig {
            backend: "candle".to_string(),
            model_path: Some(dir.path().join("missing.gguf")),
            ..Default::default()
        };
        let engine = InferenceEngine::new(&config).await.unwrap();
        assert!(matches!(engine.backend, Backend::Mock));
    }

    #[test]
    fn parse_ollama_response_extracts_the_response_field() {
        let body = br#"{"model":"qwen2.5:7b","response":"Try `lsof -i :PORT`.","done":true}"#;
        assert_eq!(parse_ollama_response(body).unwrap(), "Try `lsof -i :PORT`.");
    }

    #[test]
    fn parse_ollama_response_rejects_malformed_json() {
        assert!(parse_ollama_response(b"not json at all").is_err());
    }

    #[test]
    fn parse_ollama_response_rejects_missing_response_field() {
        assert!(parse_ollama_response(br#"{"model":"qwen2.5:7b","done":true}"#).is_err());
    }
}

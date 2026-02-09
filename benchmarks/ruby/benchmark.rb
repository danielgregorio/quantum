#!/usr/bin/env ruby
# frozen_string_literal: true

# Quantum Comparison Benchmarks - Ruby Edition
#
# Run: ruby benchmark.rb
#
# Equivalent benchmarks to compare with Quantum Framework

require 'json'
require 'benchmark'
require 'sqlite3'

class BenchmarkRunner
  def initialize
    @results = {}
  end

  def run(name, iterations, &block)
    # Warmup
    warmup = [100, iterations / 10].min
    warmup.times { block.call }

    # Benchmark
    times = []
    iterations.times do
      start = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
      block.call
      finish = Process.clock_gettime(Process::CLOCK_MONOTONIC, :nanosecond)
      times << (finish - start) / 1_000_000.0 # Convert to ms
    end

    total = times.sum
    avg = total / times.length
    min_t = times.min
    max_t = times.max
    ops_per_sec = 1000.0 / avg

    @results[name] = {
      iterations: iterations,
      total_ms: total,
      avg_ms: avg,
      min_ms: min_t,
      max_ms: max_t,
      ops_per_sec: ops_per_sec
    }

    printf "  %-35s %8.4f ms  %12.0f ops/sec\n", name, avg, ops_per_sec

    @results[name]
  end

  def results
    @results
  end

  def save_results(filename)
    data = {
      platform: 'Ruby',
      version: RUBY_VERSION,
      timestamp: Time.now.iso8601,
      results: @results
    }
    File.write(filename, JSON.pretty_generate(data))
  end
end

# =============================================================================
# Start Benchmarks
# =============================================================================

puts
puts "=" * 70
puts "  RUBY BENCHMARKS - Comparison with Quantum Framework"
puts "=" * 70
puts "  Ruby Version: #{RUBY_VERSION}"
puts "=" * 70
puts

bench = BenchmarkRunner.new

# =============================================================================
# Variable Operations
# =============================================================================

puts "  [VARIABLES]"
puts "-" * 70

bench.run('variable_assign', 100_000) do
  x = 42
  y = "hello"
  z = [1, 2, 3]
end

bench.run('variable_arithmetic', 100_000) do
  a = 10
  b = 20
  c = 30
  result = a + b * c - a / 2
end

# =============================================================================
# Loops
# =============================================================================

puts
puts "  [LOOPS]"
puts "-" * 70

bench.run('loop_100', 10_000) do
  sum = 0
  100.times { |i| sum += i }
end

bench.run('loop_1000', 1_000) do
  sum = 0
  1000.times { |i| sum += i }
end

bench.run('each_100', 10_000) do
  items = (1..100).to_a
  sum = 0
  items.each { |item| sum += item }
end

# =============================================================================
# Arrays
# =============================================================================

puts
puts "  [ARRAYS]"
puts "-" * 70

bench.run('array_create_100', 10_000) do
  arr = []
  100.times { |i| arr << i }
end

bench.run('array_map', 5_000) do
  items = (1..100).to_a
  mapped = items.map { |x| x * 2 }
end

bench.run('array_select', 5_000) do
  items = (1..100).to_a
  filtered = items.select { |x| x.even? }
end

bench.run('array_reduce', 5_000) do
  items = (1..100).to_a
  sum = items.reduce(0) { |acc, x| acc + x }
end

# =============================================================================
# Hashes (Dicts)
# =============================================================================

puts
puts "  [HASHES]"
puts "-" * 70

bench.run('hash_create', 10_000) do
  hash = {}
  100.times { |i| hash["key#{i}"] = i }
end

bench.run('hash_access', 10_000) do
  hash = {}
  100.times { |i| hash["key#{i}"] = i }
  values = []
  100.times { |i| values << hash["key#{i}"] }
end

# =============================================================================
# JSON
# =============================================================================

puts
puts "  [JSON]"
puts "-" * 70

json_small = '{"name": "Alice", "age": 30, "email": "alice@example.com"}'
json_medium = { users: (1..100).map { |i| { id: i, name: "User#{i}", email: "user#{i}@example.com" } } }.to_json

bench.run('json_parse_small', 10_000) do
  data = JSON.parse(json_small)
end

bench.run('json_parse_medium', 1_000) do
  data = JSON.parse(json_medium)
end

bench.run('json_serialize_small', 10_000) do
  data = { name: 'Alice', age: 30, email: 'alice@example.com' }
  json = data.to_json
end

bench.run('json_serialize_medium', 1_000) do
  data = { users: (1..100).map { |i| { id: i, name: "User#{i}", email: "user#{i}@example.com" } } }
  json = data.to_json
end

# =============================================================================
# Methods/Functions
# =============================================================================

puts
puts "  [METHODS]"
puts "-" * 70

def add(a, b)
  a + b
end

bench.run('method_call', 100_000) do
  result = add(10, 20)
end

bench.run('lambda_call', 50_000) do
  add_lambda = ->(a, b) { a + b }
  result = add_lambda.call(10, 20)
end

bench.run('proc_call', 50_000) do
  add_proc = Proc.new { |a, b| a + b }
  result = add_proc.call(10, 20)
end

# =============================================================================
# Classes
# =============================================================================

puts
puts "  [CLASSES]"
puts "-" * 70

class Calculator
  def initialize(initial = 0)
    @value = initial
  end

  def add(x)
    @value += x
    self
  end

  def result
    @value
  end
end

bench.run('class_instantiate', 50_000) do
  calc = Calculator.new(10)
end

bench.run('class_method_chain', 20_000) do
  calc = Calculator.new(10)
  result = calc.add(5).add(3).result
end

# =============================================================================
# Strings
# =============================================================================

puts
puts "  [STRINGS]"
puts "-" * 70

bench.run('string_concat', 10_000) do
  s = ""
  100.times { s += "hello" }
end

bench.run('string_interpolation', 50_000) do
  name = "Alice"
  age = 30
  message = "Hello, #{name}! You are #{age} years old."
end

bench.run('string_gsub', 10_000) do
  text = "Hello World! Hello Universe! Hello Everyone!"
  result = text.gsub("Hello", "Hi")
end

bench.run('regex_match', 10_000) do
  text = "Contact: alice@example.com, bob@test.org"
  matches = text.scan(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/)
end

# =============================================================================
# Database (SQLite)
# =============================================================================

puts
puts "  [DATABASE]"
puts "-" * 70

bench.run('sqlite_query', 1_000) do
  db = SQLite3::Database.new(':memory:')
  db.execute('CREATE TABLE test (id INTEGER, value TEXT)')
  db.execute("INSERT INTO test VALUES (1, 'test')")
  result = db.execute('SELECT * FROM test')
  db.close
end

# =============================================================================
# Template/String Processing
# =============================================================================

puts
puts "  [TEMPLATES]"
puts "-" * 70

template = '<html><head><title>{{title}}</title></head><body><h1>{{heading}}</h1><p>{{content}}</p></body></html>'

bench.run('template_simple', 10_000) do
  html = template
    .gsub('{{title}}', 'My Page')
    .gsub('{{heading}}', 'Welcome')
    .gsub('{{content}}', 'Hello World')
end

bench.run('template_loop', 2_000) do
  items = (1..20).to_a
  html = '<ul>'
  items.each { |item| html += "<li>Item #{item}</li>" }
  html += '</ul>'
end

# ERB template (if available)
begin
  require 'erb'

  erb_template = '<ul><% items.each do |item| %><li><%= item %></li><% end %></ul>'

  bench.run('erb_template', 2_000) do
    items = (1..20).to_a
    template = ERB.new(erb_template)
    html = template.result(binding)
  end
rescue LoadError
  puts "  (ERB not available, skipping)"
end

# =============================================================================
# Summary
# =============================================================================

puts
puts "=" * 70
puts "  SUMMARY"
puts "=" * 70

results = bench.results
total_ops = results.values.map { |r| r[:iterations] }.sum
total_time = results.values.map { |r| r[:total_ms] }.sum

puts "  Total benchmarks: #{results.length}"
puts "  Total iterations: #{total_ops.to_s.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse}"
puts "  Total time: #{'%.2f' % (total_time / 1000)} seconds"
puts "=" * 70
puts

# Save results
bench.save_results('ruby_benchmark_results.json')
puts "Results saved to: ruby_benchmark_results.json"

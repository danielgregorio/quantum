<?php
/**
 * Quantum Comparison Benchmarks - PHP Edition
 *
 * Run: php benchmark.php
 *
 * Equivalent benchmarks to compare with Quantum Framework
 */

class Benchmark {
    private $results = [];

    public function run($name, $iterations, $callback) {
        // Warmup
        for ($i = 0; $i < min(100, $iterations / 10); $i++) {
            $callback();
        }

        // Benchmark
        $times = [];
        for ($i = 0; $i < $iterations; $i++) {
            $start = hrtime(true);
            $callback();
            $end = hrtime(true);
            $times[] = ($end - $start) / 1000000; // Convert to ms
        }

        $total = array_sum($times);
        $avg = $total / count($times);
        $min = min($times);
        $max = max($times);
        $ops_per_sec = 1000 / $avg;

        $this->results[$name] = [
            'iterations' => $iterations,
            'total_ms' => $total,
            'avg_ms' => $avg,
            'min_ms' => $min,
            'max_ms' => $max,
            'ops_per_sec' => $ops_per_sec
        ];

        printf("  %-35s %8.4f ms  %12.0f ops/sec\n", $name, $avg, $ops_per_sec);

        return $this->results[$name];
    }

    public function getResults() {
        return $this->results;
    }

    public function saveResults($filename) {
        file_put_contents($filename, json_encode([
            'platform' => 'PHP',
            'version' => phpversion(),
            'timestamp' => date('c'),
            'results' => $this->results
        ], JSON_PRETTY_PRINT));
    }
}

// =============================================================================
// Variable Operations
// =============================================================================

echo "\n";
echo "======================================================================\n";
echo "  PHP BENCHMARKS - Comparison with Quantum Framework\n";
echo "======================================================================\n";
echo "  PHP Version: " . phpversion() . "\n";
echo "======================================================================\n\n";

$bench = new Benchmark();

echo "  [VARIABLES]\n";
echo "----------------------------------------------------------------------\n";

$bench->run('variable_assign', 100000, function() {
    $x = 42;
    $y = "hello";
    $z = [1, 2, 3];
});

$bench->run('variable_arithmetic', 100000, function() {
    $a = 10;
    $b = 20;
    $c = 30;
    $result = $a + $b * $c - $a / 2;
});

// =============================================================================
// Loops
// =============================================================================

echo "\n  [LOOPS]\n";
echo "----------------------------------------------------------------------\n";

$bench->run('loop_100', 10000, function() {
    $sum = 0;
    for ($i = 0; $i < 100; $i++) {
        $sum += $i;
    }
});

$bench->run('loop_1000', 1000, function() {
    $sum = 0;
    for ($i = 0; $i < 1000; $i++) {
        $sum += $i;
    }
});

$bench->run('foreach_100', 10000, function() {
    $items = range(1, 100);
    $sum = 0;
    foreach ($items as $item) {
        $sum += $item;
    }
});

// =============================================================================
// Arrays/Lists
// =============================================================================

echo "\n  [ARRAYS]\n";
echo "----------------------------------------------------------------------\n";

$bench->run('array_create_100', 10000, function() {
    $arr = [];
    for ($i = 0; $i < 100; $i++) {
        $arr[] = $i;
    }
});

$bench->run('array_map', 5000, function() {
    $items = range(1, 100);
    $mapped = array_map(function($x) { return $x * 2; }, $items);
});

$bench->run('array_filter', 5000, function() {
    $items = range(1, 100);
    $filtered = array_filter($items, function($x) { return $x % 2 == 0; });
});

$bench->run('array_reduce', 5000, function() {
    $items = range(1, 100);
    $sum = array_reduce($items, function($carry, $item) { return $carry + $item; }, 0);
});

// =============================================================================
// Associative Arrays (Dicts)
// =============================================================================

echo "\n  [ASSOCIATIVE ARRAYS]\n";
echo "----------------------------------------------------------------------\n";

$bench->run('dict_create', 10000, function() {
    $dict = [];
    for ($i = 0; $i < 100; $i++) {
        $dict["key$i"] = $i;
    }
});

$bench->run('dict_access', 10000, function() {
    $dict = [];
    for ($i = 0; $i < 100; $i++) {
        $dict["key$i"] = $i;
    }
    $values = [];
    for ($i = 0; $i < 100; $i++) {
        $values[] = $dict["key$i"];
    }
});

// =============================================================================
// JSON
// =============================================================================

echo "\n  [JSON]\n";
echo "----------------------------------------------------------------------\n";

$json_small = '{"name": "Alice", "age": 30, "email": "alice@example.com"}';
$json_medium = json_encode(['users' => array_map(function($i) {
    return ['id' => $i, 'name' => "User$i", 'email' => "user$i@example.com"];
}, range(1, 100))]);

$bench->run('json_parse_small', 10000, function() use ($json_small) {
    $data = json_decode($json_small, true);
});

$bench->run('json_parse_medium', 1000, function() use ($json_medium) {
    $data = json_decode($json_medium, true);
});

$bench->run('json_serialize_small', 10000, function() {
    $data = ['name' => 'Alice', 'age' => 30, 'email' => 'alice@example.com'];
    $json = json_encode($data);
});

$bench->run('json_serialize_medium', 1000, function() {
    $data = ['users' => array_map(function($i) {
        return ['id' => $i, 'name' => "User$i", 'email' => "user$i@example.com"];
    }, range(1, 100))];
    $json = json_encode($data);
});

// =============================================================================
// Functions
// =============================================================================

echo "\n  [FUNCTIONS]\n";
echo "----------------------------------------------------------------------\n";

function add($a, $b) {
    return $a + $b;
}

$bench->run('function_call', 100000, function() {
    $result = add(10, 20);
});

$bench->run('closure_call', 50000, function() {
    $add = function($a, $b) { return $a + $b; };
    $result = $add(10, 20);
});

// =============================================================================
// Classes
// =============================================================================

echo "\n  [CLASSES]\n";
echo "----------------------------------------------------------------------\n";

class Calculator {
    private $value;

    public function __construct($initial = 0) {
        $this->value = $initial;
    }

    public function add($x) {
        $this->value += $x;
        return $this;
    }

    public function result() {
        return $this->value;
    }
}

$bench->run('class_instantiate', 50000, function() {
    $calc = new Calculator(10);
});

$bench->run('class_method_chain', 20000, function() {
    $calc = new Calculator(10);
    $result = $calc->add(5)->add(3)->result();
});

// =============================================================================
// String Operations
// =============================================================================

echo "\n  [STRINGS]\n";
echo "----------------------------------------------------------------------\n";

$bench->run('string_concat', 10000, function() {
    $s = "";
    for ($i = 0; $i < 100; $i++) {
        $s .= "hello";
    }
});

$bench->run('string_interpolation', 50000, function() {
    $name = "Alice";
    $age = 30;
    $message = "Hello, $name! You are $age years old.";
});

$bench->run('string_replace', 10000, function() {
    $text = "Hello World! Hello Universe! Hello Everyone!";
    $result = str_replace("Hello", "Hi", $text);
});

$bench->run('regex_match', 10000, function() {
    $text = "Contact: alice@example.com, bob@test.org";
    preg_match_all('/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/', $text, $matches);
});

// =============================================================================
// Database (SQLite)
// =============================================================================

echo "\n  [DATABASE]\n";
echo "----------------------------------------------------------------------\n";

$bench->run('sqlite_query', 1000, function() {
    $db = new SQLite3(':memory:');
    $db->exec('CREATE TABLE test (id INTEGER, value TEXT)');
    $db->exec("INSERT INTO test VALUES (1, 'test')");
    $result = $db->query('SELECT * FROM test');
    $row = $result->fetchArray();
    $db->close();
});

// =============================================================================
// Template/String Processing (simulating view rendering)
// =============================================================================

echo "\n  [TEMPLATES]\n";
echo "----------------------------------------------------------------------\n";

$template = '<html><head><title>{{title}}</title></head><body><h1>{{heading}}</h1><p>{{content}}</p></body></html>';

$bench->run('template_simple', 10000, function() use ($template) {
    $html = str_replace(
        ['{{title}}', '{{heading}}', '{{content}}'],
        ['My Page', 'Welcome', 'Hello World'],
        $template
    );
});

$bench->run('template_loop', 2000, function() {
    $items = range(1, 20);
    $html = '<ul>';
    foreach ($items as $item) {
        $html .= "<li>Item $item</li>";
    }
    $html .= '</ul>';
});

// =============================================================================
// Summary
// =============================================================================

echo "\n======================================================================\n";
echo "  SUMMARY\n";
echo "======================================================================\n";

$results = $bench->getResults();
$total_ops = array_sum(array_column($results, 'iterations'));
$total_time = array_sum(array_column($results, 'total_ms'));

printf("  Total benchmarks: %d\n", count($results));
printf("  Total iterations: %s\n", number_format($total_ops));
printf("  Total time: %.2f seconds\n", $total_time / 1000);
echo "======================================================================\n\n";

// Save results
$bench->saveResults('php_benchmark_results.json');
echo "Results saved to: php_benchmark_results.json\n";

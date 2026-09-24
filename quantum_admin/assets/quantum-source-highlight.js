(function(){
  var code = document.getElementById('sourceCode');
  var gutter = document.getElementById('sourceGutter');
  if(!code || !gutter) return;

  var html = code.innerHTML;
  var lines = html.split('\n');

  // Build gutter line numbers
  var g = '';
  for(var i = 1; i <= lines.length; i++) g += '<div>' + i + '</div>';
  gutter.innerHTML = g;

  // Detect file type from page title (format: "Source: path/file.ext - Quantum Admin")
  var ext = '';
  var title = document.title || '';
  var m = title.match(/\.(\w+)\s/);
  if(m) ext = m[1].toLowerCase();

  // Escaped entities in rendered HTML
  var LT = '&lt;';
  var GT = '&gt;';
  var QUOT = '&quot;';
  var AMP = '&amp;';
  var APOS = '&#x27;';

  function s(cls, content) {
    return '<span class="' + cls + '">' + content + '</span>';
  }

  var h = html;

  if(ext === 'q' || ext === 'html' || ext === 'xml') {
    // Comments: &lt;!-- ... --&gt;
    h = h.replace(new RegExp(LT + '!--[\\s\\S]*?--' + GT, 'g'), function(m){ return s('hl-cmt', m); });
    // Tags: &lt;tagname and &lt;/tagname
    h = h.replace(new RegExp('(' + LT + '\\/?)((?:[a-zA-Z][\\w:.-]*))', 'g'), function(m, pre, tag){
      return s('hl-punct', pre) + s('hl-tag', tag);
    });
    // Closing &gt;
    h = h.replace(new RegExp('(\\/?\\s*)' + GT, 'g'), function(m, pre){
      return pre + s('hl-punct', GT);
    });
    // Attributes: name="value"
    h = h.replace(new RegExp('([a-zA-Z][\\w:-]*)=' + QUOT + '([^]*?)' + QUOT, 'g'), function(m, attr, val){
      return s('hl-attr', attr) + '=' + s('hl-str', QUOT + val + QUOT);
    });
    // SQL keywords (for q:query content)
    h = h.replace(/\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|NOT|ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT|OFFSET|AS|INTO|VALUES|SET|CREATE|DROP|ALTER|TABLE|INDEX|DISTINCT|COUNT|SUM|AVG|MAX|MIN|FILTER|TRUE|FALSE|DESC|ASC|LIKE|IN|IS|NULL|BETWEEN|EXISTS|UNION|CASE|WHEN|THEN|ELSE|END)\b/g, function(m){ return s('hl-sql', m); });
    // Databinding expressions {var}
    h = h.replace(/(\{[^}<\n]+?\})/g, function(m){ return s('hl-var', m); });
  } else if(ext === 'py') {
    // Comments (careful not to match inside strings)
    h = h.replace(/(#[^\n]*)/g, function(m){ return s('hl-cmt', m); });
    // Strings
    h = h.replace(new RegExp('(f?' + QUOT + '[^' + AMP + ']*?' + QUOT + ')', 'g'), function(m){ return s('hl-str', m); });
    h = h.replace(new RegExp("(f?'[^'\\n]*')", 'g'), function(m){ return s('hl-str', m); });
    // Keywords
    h = h.replace(/\b(def|class|import|from|return|if|elif|else|for|while|try|except|finally|with|as|raise|pass|break|continue|yield|lambda|in|not|and|or|is|True|False|None|self|async|await|global|nonlocal)\b/g, function(m){ return s('hl-kw', m); });
    // Decorators
    h = h.replace(/(@\w+)/g, function(m){ return s('hl-dec', m); });
    // Numbers
    h = h.replace(/\b(\d+\.?\d*)\b/g, function(m){ return s('hl-num', m); });
    // Built-in functions
    h = h.replace(/\b(print|len|range|str|int|float|list|dict|set|tuple|open|type|isinstance|getattr|setattr|hasattr|enumerate|zip|map|filter|sorted|reversed|super|property|staticmethod|classmethod)\b(?=\s*\()/g, function(m){ return s('hl-fn', m); });
  } else if(ext === 'yaml' || ext === 'yml') {
    h = h.replace(/(#[^\n]*)/g, function(m){ return s('hl-cmt', m); });
    h = h.replace(/^(\s*)([\w][\w.-]*)(:)/gm, function(m, sp, key, colon){
      return sp + s('hl-attr', key) + s('hl-punct', colon);
    });
    h = h.replace(/\b(true|false|null|yes|no)\b/gi, function(m){ return s('hl-kw', m); });
    h = h.replace(/\b(\d+\.?\d*)\b/g, function(m){ return s('hl-num', m); });
  } else if(ext === 'json') {
    h = h.replace(new RegExp('(' + QUOT + '[^' + AMP + ']*?' + QUOT + ')\\s*:', 'g'), function(m, key){
      return s('hl-attr', key) + ':';
    });
    h = h.replace(new RegExp(':\\s*(' + QUOT + '[^' + AMP + ']*?' + QUOT + ')', 'g'), function(m, val){
      return ': ' + s('hl-str', val);
    });
    h = h.replace(/\b(true|false|null)\b/g, function(m){ return s('hl-kw', m); });
    h = h.replace(/\b(\d+\.?\d*)\b/g, function(m){ return s('hl-num', m); });
  } else if(ext === 'css') {
    h = h.replace(/(\/\*[\s\S]*?\*\/)/g, function(m){ return s('hl-cmt', m); });
    h = h.replace(/([\w-]+)\s*(?=:)/g, function(m, prop){ return s('hl-attr', prop); });
    h = h.replace(/(\d+\.?\d*)(px|em|rem|%|vh|vw|s|ms|deg)/g, function(m, num, unit){ return s('hl-num', num + unit); });
    h = h.replace(/(#[0-9a-fA-F]{3,8})\b/g, function(m){ return s('hl-num', m); });
  } else if(ext === 'js' || ext === 'ts') {
    h = h.replace(/(\/\/[^\n]*)/g, function(m){ return s('hl-cmt', m); });
    h = h.replace(/(\/\*[\s\S]*?\*\/)/g, function(m){ return s('hl-cmt', m); });
    h = h.replace(new RegExp("('[^'\\n]*'|" + QUOT + '[^' + AMP + ']*?' + QUOT + '|`[^`]*`)', 'g'), function(m){ return s('hl-str', m); });
    h = h.replace(/\b(function|const|let|var|return|if|else|for|while|do|switch|case|break|continue|class|new|this|import|export|from|default|async|await|try|catch|finally|throw|typeof|instanceof|in|of|true|false|null|undefined|void|delete)\b/g, function(m){ return s('hl-kw', m); });
    h = h.replace(/\b(\d+\.?\d*)\b/g, function(m){ return s('hl-num', m); });
  } else if(ext === 'md') {
    // Headers
    h = h.replace(/^(#{1,6}\s+.*)$/gm, function(m){ return s('hl-tag', m); });
    // Bold/italic
    h = h.replace(/(\*\*[^*]+\*\*)/g, function(m){ return s('hl-kw', m); });
    h = h.replace(/(\*[^*]+\*)/g, function(m){ return s('hl-str', m); });
    // Code blocks
    h = h.replace(/(`[^`]+`)/g, function(m){ return s('hl-fn', m); });
    // Links
    h = h.replace(/(\[[^\]]+\]\([^)]+\))/g, function(m){ return s('hl-attr', m); });
  }

  code.innerHTML = h;
})();

<q:component name="BlogStyles" type="partial">
  <!--
    Shared CSS styles for the Quantum Blog
  -->

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=Merriweather:wght@400;700&amp;display=swap');

    :root {
      --primary: #6366f1;
      --primary-dark: #4f46e5;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
      --bg-dark: #0f172a;
      --bg-card: #ffffff;
      --bg-page: #f8fafc;
      --text-primary: #1e293b;
      --text-secondary: #64748b;
      --text-muted: #94a3b8;
      --border: #e2e8f0;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Inter', -apple-system, sans-serif; background: var(--bg-page); color: var(--text-primary); }

    /* Header */
    header {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
      border-bottom: 2px solid var(--primary);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header-inner {
      max-width: 1000px; margin: 0 auto; padding: 16px 24px;
      display: flex; justify-content: space-between; align-items: center;
    }
    .logo { color: #fff; font-size: 1.25rem; font-weight: 700; text-decoration: none; display: flex; align-items: center; gap: 10px; }
    .logo-icon { background: var(--primary); color: white; width: 32px; height: 32px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1rem; }
    nav { display: flex; align-items: center; gap: 6px; }
    nav a {
      color: #94a3b8; text-decoration: none; font-size: 0.85rem; font-weight: 500;
      padding: 6px 14px; border-radius: 6px; transition: all 0.2s;
    }
    nav a:hover { color: #e2e8f0; background: rgba(255,255,255,0.08); }

    /* Hero */
    .hero {
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #312e81 100%);
      padding: 64px 24px 56px; text-align: center; position: relative; overflow: hidden;
    }
    .hero::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
      background: radial-gradient(circle at 30% 50%, rgba(99,102,241,0.15) 0%, transparent 50%),
                  radial-gradient(circle at 70% 50%, rgba(139,92,246,0.1) 0%, transparent 50%);
    }
    .hero-content { position: relative; z-index: 1; max-width: 600px; margin: 0 auto; }
    .hero h1 { color: #fff; font-size: 2.5rem; font-weight: 800; margin-bottom: 12px; letter-spacing: -0.02em; }
    .hero h1 span { background: linear-gradient(135deg, #818cf8, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { color: #94a3b8; font-size: 1.1rem; line-height: 1.6; }
    .hero-stats { display: flex; justify-content: center; gap: 32px; margin-top: 28px; }
    .hero-stat { color: #cbd5e1; font-size: 0.85rem; }
    .hero-stat strong { display: block; font-size: 1.5rem; color: #fff; font-weight: 700; }

    /* Main */
    .main { max-width: 1000px; margin: 0 auto; padding: 48px 24px; }
    .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; flex-wrap: wrap; gap: 16px; }
    .section-title { font-size: 1.3rem; font-weight: 700; color: var(--bg-dark); }
    .post-count-badge { background: #ede9fe; color: #6d28d9; font-size: 0.8rem; font-weight: 600; padding: 4px 12px; border-radius: 20px; }

    /* Post cards */
    .posts-grid { display: flex; flex-direction: column; gap: 20px; }
    .post-card {
      background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
      padding: 28px 32px; transition: all 0.25s ease;
      display: block; text-decoration: none; color: inherit;
    }
    .post-card:hover { border-color: #c7d2fe; box-shadow: 0 8px 24px rgba(99,102,241,0.08); transform: translateY(-2px); }
    .post-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .post-tag { font-size: 0.75rem; font-weight: 600; padding: 3px 10px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
    .post-date { color: var(--text-muted); font-size: 0.8rem; }
    .post-card h2 { font-size: 1.25rem; font-weight: 700; color: var(--bg-dark); margin-bottom: 8px; line-height: 1.4; }
    .post-card p { color: var(--text-secondary); font-size: 0.95rem; line-height: 1.7; }
    .post-card .post-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid #f1f5f9; }
    .post-author { display: flex; align-items: center; gap: 8px; }
    .author-avatar { width: 28px; height: 28px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; color: white; font-size: 0.7rem; font-weight: 700; }
    .author-name { font-size: 0.85rem; color: #475569; font-weight: 500; }
    .post-meta-right { display: flex; align-items: center; gap: 16px; }
    .post-views { color: var(--text-muted); font-size: 0.8rem; }
    .read-more { color: var(--primary); font-size: 0.85rem; font-weight: 600; }

    /* Pagination */
    .pagination { display: flex; justify-content: center; gap: 8px; margin-top: 40px; }
    .pagination a, .pagination span {
      padding: 8px 16px; border-radius: 8px; font-size: 0.9rem; font-weight: 500;
      text-decoration: none; transition: all 0.2s;
    }
    .pagination a { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary); }
    .pagination a:hover { border-color: var(--primary); color: var(--primary); }
    .pagination .current { background: var(--primary); color: white; border: none; }
    .pagination .disabled { opacity: 0.5; cursor: not-allowed; }

    /* Search */
    .search-box {
      display: flex; gap: 12px; margin-bottom: 32px;
    }
    .search-input {
      flex: 1; padding: 12px 16px; border: 1px solid var(--border); border-radius: 8px;
      font-size: 1rem; background: var(--bg-card); color: var(--text-primary);
    }
    .search-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
    .search-btn {
      padding: 12px 24px; background: var(--primary); color: white; border: none;
      border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s;
    }
    .search-btn:hover { background: var(--primary-dark); }

    /* Tags filter */
    .tags-filter { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px; }
    .tag-pill {
      padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 500;
      text-decoration: none; transition: all 0.2s; border: 1px solid var(--border);
      color: var(--text-secondary); background: var(--bg-card);
    }
    .tag-pill:hover, .tag-pill.active { border-color: var(--primary); color: var(--primary); background: #ede9fe; }

    /* Footer */
    footer { max-width: 1000px; margin: 0 auto; padding: 32px 24px; border-top: 1px solid var(--border); }
    .footer-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
    .footer-brand { font-size: 0.85rem; color: var(--text-muted); }
    .footer-brand strong { color: var(--primary); }
    .footer-links a { color: var(--text-muted); text-decoration: none; font-size: 0.8rem; margin-left: 16px; }
    .footer-links a:hover { color: var(--primary); }

    /* Article view */
    .article-container { max-width: 720px; margin: 0 auto; padding: 48px 24px 64px; }
    .post-header { margin-bottom: 40px; }
    .post-title { font-size: 2.2rem; font-weight: 800; color: var(--bg-dark); line-height: 1.3; margin-bottom: 20px; letter-spacing: -0.02em; }
    .post-meta { display: flex; align-items: center; gap: 16px; padding-bottom: 24px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
    .meta-author { display: flex; align-items: center; gap: 10px; }
    .author-info { display: flex; flex-direction: column; }
    .author-date { font-size: 0.8rem; color: var(--text-muted); }
    .post-content {
      font-family: 'Merriweather', Georgia, serif;
      font-size: 1.05rem; line-height: 1.9; color: #374151;
    }
    .post-content p { margin-bottom: 1.5em; }
    .post-content h2 { font-family: 'Inter', sans-serif; font-size: 1.5rem; font-weight: 700; margin: 2em 0 1em; color: var(--text-primary); }
    .post-content pre { background: var(--bg-dark); color: #e2e8f0; padding: 20px; border-radius: 8px; overflow-x: auto; margin: 1.5em 0; }
    .post-content code { font-family: 'JetBrains Mono', monospace; font-size: 0.9em; }
    .back-bar { margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--border); }
    .back-link {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 10px 20px; background: #f1f5f9; color: var(--primary);
      text-decoration: none; border-radius: 8px; font-size: 0.9rem; font-weight: 600;
      transition: all 0.2s;
    }
    .back-link:hover { background: #e2e8f0; }

    /* AI Summary box */
    .ai-summary {
      background: linear-gradient(135deg, #ede9fe 0%, #fae8ff 100%);
      border: 1px solid #c4b5fd;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 32px;
    }
    .ai-summary-header {
      display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
      font-size: 0.8rem; font-weight: 600; color: #7c3aed; text-transform: uppercase;
    }
    .ai-summary p { font-size: 0.95rem; color: #581c87; line-height: 1.6; margin: 0; }

    /* Related posts */
    .related-posts { margin-top: 48px; padding-top: 32px; border-top: 1px solid var(--border); }
    .related-posts h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 20px; }
    .related-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; }
    .related-card {
      padding: 16px; background: var(--bg-card); border: 1px solid var(--border);
      border-radius: 8px; text-decoration: none; color: inherit; transition: all 0.2s;
    }
    .related-card:hover { border-color: var(--primary); }
    .related-card h4 { font-size: 0.95rem; font-weight: 600; margin-bottom: 4px; }
    .related-card p { font-size: 0.8rem; color: var(--text-muted); }

    /* Comments */
    .comments-section { margin-top: 48px; padding-top: 32px; border-top: 1px solid var(--border); }
    .comments-section h3 { font-size: 1.1rem; font-weight: 700; margin-bottom: 24px; }
    .comment {
      padding: 16px 0; border-bottom: 1px solid #f1f5f9;
    }
    .comment-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
    .comment-author { font-weight: 600; font-size: 0.9rem; }
    .comment-date { font-size: 0.8rem; color: var(--text-muted); }
    .comment-content { font-size: 0.95rem; line-height: 1.6; color: var(--text-secondary); }
    .comment-form { margin-top: 24px; }
    .comment-form textarea {
      width: 100%; padding: 12px; border: 1px solid var(--border); border-radius: 8px;
      font-size: 0.95rem; min-height: 100px; resize: vertical; margin-bottom: 12px;
    }

    /* Forms */
    .form-card {
      background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
      padding: 32px; margin-bottom: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .form-card h2 { font-size: 1.1rem; font-weight: 700; margin-bottom: 24px; color: var(--bg-dark); }
    .form-group { margin-bottom: 20px; }
    .form-group label { display: block; font-weight: 600; font-size: 0.8rem; color: #475569; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.03em; }
    .form-group input, .form-group textarea, .form-group select {
      width: 100%; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px;
      font-size: 0.95rem; font-family: inherit; background: var(--bg-card); color: var(--text-primary);
      transition: all 0.2s;
    }
    .form-group input:focus, .form-group textarea:focus, .form-group select:focus {
      outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
    }
    .form-group textarea { min-height: 140px; resize: vertical; line-height: 1.6; }
    .btn-primary {
      padding: 12px 28px; background: var(--primary); color: white; border: none;
      border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer;
      transition: all 0.2s;
    }
    .btn-primary:hover { background: var(--primary-dark); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(99,102,241,0.25); }

    /* Not found */
    .not-found { text-align: center; padding: 100px 20px; }
    .nf-code { font-size: 3.5rem; font-weight: 800; color: #e2e8f0; margin-bottom: 12px; }
    .not-found h2 { font-size: 1.5rem; color: var(--text-secondary); margin-bottom: 8px; }
    .not-found p { color: var(--text-muted); margin-bottom: 24px; }

    /* Responsive */
    @media (max-width: 640px) {
      .hero h1 { font-size: 1.8rem; }
      .hero-stats { gap: 20px; }
      .post-card { padding: 20px; }
      .post-title { font-size: 1.6rem; }
      .post-content { font-size: 1rem; }
      .footer-content { flex-direction: column; text-align: center; }
    }
  </style>

</q:component>

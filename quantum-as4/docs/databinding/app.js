import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "layout": "vertical"
  },
  "events": {},
  "children": [
    {
      "type": "VBox",
      "props": {
        "padding": "20",
        "gap": "10"
      },
      "events": {},
      "children": [
        {
          "type": "Label",
          "props": {
            "text": "Data Binding Example",
            "fontSize": "18",
            "fontWeight": "bold"
          },
          "events": {},
          "children": []
        },
        {
          "type": "Label",
          "props": {
            "text": "Welcome, {username}!"
          },
          "events": {},
          "children": []
        },
        {
          "type": "Label",
          "props": {
            "text": "Count: {count}"
          },
          "events": {},
          "children": []
        },
        {
          "type": "Button",
          "props": {
            "label": "Increment"
          },
          "events": {
            "click": "incrementCount()"
          },
          "children": []
        }
      ]
    }
  ]
};

// Application Class (from ActionScript)
class App {
  constructor(runtime) {
    this.runtime = runtime;

    this.username = "John Doe";
    this.count = 0;
  }

  incrementCount() {
    this.count++;
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));

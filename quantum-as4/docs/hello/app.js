import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "title": "Hello World - ActionScript 4"
  },
  "events": {},
  "children": [
    {
      "type": "VBox",
      "props": {
        "padding": "40",
        "gap": "20",
        "width": "600"
      },
      "events": {},
      "children": [
        {
          "type": "Label",
          "props": {
            "text": "ActionScript 4 + MXML",
            "styleName": "title"
          },
          "events": {},
          "children": []
        },
        {
          "type": "Label",
          "props": {
            "text": "{message}",
            "styleName": "subtitle"
          },
          "events": {},
          "children": []
        },
        {
          "type": "HBox",
          "props": {
            "gap": "10"
          },
          "events": {},
          "children": [
            {
              "type": "Button",
              "props": {
                "label": "Click Me!"
              },
              "events": {
                "click": "handleClick()"
              },
              "children": []
            },
            {
              "type": "Button",
              "props": {
                "label": "Reset",
                "styleName": "reset-button"
              },
              "events": {
                "click": "handleReset()"
              },
              "children": []
            }
          ]
        },
        {
          "type": "Panel",
          "props": {
            "title": "Info"
          },
          "events": {},
          "children": [
            {
              "type": "VBox",
              "props": {
                "padding": "15",
                "gap": "10"
              },
              "events": {},
              "children": [
                {
                  "type": "Label",
                  "props": {
                    "text": "This is a demo of:"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 MXML declarative UI"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 ActionScript 4 event handlers"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 Data binding with {curly braces}"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 CSS styling"
                  },
                  "events": {},
                  "children": []
                },
                {
                  "type": "Label",
                  "props": {
                    "text": "\u2022 Flex Spark components"
                  },
                  "events": {},
                  "children": []
                }
              ]
            }
          ]
        }
      ]
    }
  ]
};

// Application Class (from ActionScript)
class App {
  constructor(runtime) {
    this.runtime = runtime;

    this.message = "Hello, ActionScript 4!";
    this.clickCount = 0;
  }

  handleClick() {
    this.clickCount = this.clickCount + 1;
    this.message = "You clicked " + this.clickCount + " times!";
  }

  handleReset() {
    this.clickCount = 0;
    this.message = "Hello, ActionScript 4!";
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));

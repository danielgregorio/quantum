import { ReactiveRuntime } from './reactive-runtime.js';

// UI Component Tree
const componentTree = {
  "type": "Application",
  "props": {
    "pageTitle": "StopWatch - A PureMVC AS3 StateMachine Demo",
    "themeColor": "HaloBlue",
    "layout": "vertical",
    "horizontalAlign": "center",
    "paddingBottom": "0",
    "paddingRight": "0",
    "paddingLeft": "0",
    "paddingTop": "0",
    "backgroundGradientColors": "[#325EC0,#FFFFFF]",
    "backgroundColor": "#FFFFFF"
  },
  "events": {
    "creationComplete": "facade.startup(this)"
  },
  "children": [
    {
      "type": "ApplicationControlBar",
      "props": {
        "dock": "true"
      },
      "events": {},
      "children": [
        {
          "type": "HBox",
          "props": {
            "id": "toolbarLeft",
            "horizontalAlign": "left",
            "verticalAlign": "middle",
            "width": "33%",
            "height": "100%"
          },
          "events": {},
          "children": [
            {
              "type": "Text",
              "props": {
                "text": "StopWatch",
                "fontFamily": "Verdana",
                "fontSize": "22",
                "fontStyle": "normal",
                "color": "#0559CC"
              },
              "events": {},
              "children": []
            },
            {
              "type": "Label",
              "props": {
                "id": "statusLine",
                "fontWeight": "bold",
                "text": "A PureMVC AS3 StateMachine Demo"
              },
              "events": {},
              "children": []
            }
          ]
        },
        {
          "type": "HBox",
          "props": {
            "horizontalAlign": "center",
            "verticalAlign": "middle",
            "width": "33%",
            "height": "100%"
          },
          "events": {},
          "children": [
            {
              "type": "Text",
              "props": {
                "text": "Current State:",
                "fontFamily": "Verdana",
                "fontSize": "12",
                "fontStyle": "normal",
                "color": "#0559CC"
              },
              "events": {},
              "children": []
            },
            {
              "type": "Label",
              "props": {
                "fontWeight": "bold",
                "text": "{state}"
              },
              "events": {},
              "children": []
            }
          ]
        },
        {
          "type": "HBox",
          "props": {
            "id": "toolbarRight",
            "horizontalAlign": "right",
            "verticalAlign": "middle",
            "width": "33%",
            "height": "100%"
          },
          "events": {},
          "children": [
            {
              "type": "Button",
              "props": {
                "label": "Start",
                "enabled": "{state==STATE_READY}",
                "toolTip": "Start the StopWatch Timer."
              },
              "events": {
                "click": "sendEvent(ACTION_START)"
              },
              "children": []
            },
            {
              "type": "Button",
              "props": {
                "label": "Stop",
                "enabled": "{state==STATE_RUNNING||state==STATE_PAUSED}",
                "toolTip": "Stop the StopWatch Timer."
              },
              "events": {
                "click": "sendEvent(ACTION_STOP)"
              },
              "children": []
            },
            {
              "type": "Button",
              "props": {
                "label": "Split",
                "enabled": "{state==STATE_RUNNING}",
                "toolTip": "Split the StopWatch display."
              },
              "events": {
                "click": "sendEvent(ACTION_SPLIT)"
              },
              "children": []
            },
            {
              "type": "Button",
              "props": {
                "label": "Unsplit",
                "enabled": "{state==STATE_PAUSED}",
                "toolTip": "Unsplit the StopWatch display."
              },
              "events": {
                "click": "sendEvent(ACTION_UNSPLIT)"
              },
              "children": []
            },
            {
              "type": "Button",
              "props": {
                "label": "Reset",
                "enabled": "{state==STATE_STOPPED}",
                "toolTip": "Reset the StopWatch."
              },
              "events": {
                "click": "sendEvent(ACTION_RESET)"
              },
              "children": []
            }
          ]
        }
      ]
    },
    {
      "type": "VBox",
      "props": {
        "width": "50%",
        "height": "100%",
        "horizontalAlign": "right",
        "verticalAlign": "middle"
      },
      "events": {},
      "children": [
        {
          "type": "HBox",
          "props": {
            "horizontalAlign": "right",
            "verticalAlign": "middle"
          },
          "events": {},
          "children": [
            {
              "type": "Label",
              "props": {
                "visible": "{state!=STATE_READY}",
                "text": "Elapsed:",
                "fontSize": "32",
                "color": "#FFFFFF"
              },
              "events": {},
              "children": []
            },
            {
              "type": "Label",
              "props": {
                "id": "lblElapsed",
                "text": "{elapsed}",
                "fontSize": "64",
                "color": "#00FF00"
              },
              "events": {},
              "children": []
            }
          ]
        },
        {
          "type": "HBox",
          "props": {
            "horizontalAlign": "right",
            "verticalAlign": "middle"
          },
          "events": {},
          "children": [
            {
              "type": "Label",
              "props": {
                "text": "Lap Time:",
                "visible": "{state==STATE_PAUSED}",
                "fontSize": "32",
                "color": "#000000"
              },
              "events": {},
              "children": []
            },
            {
              "type": "Label",
              "props": {
                "id": "lblLap",
                "visible": "{state==STATE_PAUSED}",
                "text": "{laptime}",
                "fontSize": "64",
                "color": "#FF0000"
              },
              "events": {},
              "children": []
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

    this.laptime = "";
    this.elapsed = "";
    this.state = "";
    this.facade = ApplicationFacade.getInstance();
  }

  sendEvent(eventName) {
    this.dispatchEvent( new this.Event( this.eventName ) );
  }

}

// Initialize and render
const runtime = new ReactiveRuntime();
const app = new App(runtime);
runtime.setApp(app);  // Makes app reactive with Proxy
runtime.render(componentTree, document.getElementById('app'));

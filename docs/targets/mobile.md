# Mobile Target (React Native)

The Mobile target generates [React Native](https://reactnative.dev/) code for building iOS and Android applications. It transforms Quantum UI components into native mobile components using React Native's component library.

## Overview

When you build with `--target mobile`, Quantum:

1. Maps UI components to React Native equivalents
2. Generates state management with React hooks
3. Creates a StyleSheet for styling
4. Outputs a complete React Native App.js file

## Requirements

Set up a React Native development environment:

```bash
# Install Node.js and npm
# Install React Native CLI
npm install -g react-native-cli

# For iOS (macOS only)
brew install cocoapods
cd ios && pod install

# For Android
# Install Android Studio and configure ANDROID_HOME
```

## Building for Mobile

```bash
# Build UI application to React Native
python src/cli/runner.py run myapp.q --target mobile

# Output is saved as {app_id}_mobile.js (App.js compatible)
```

Create a new React Native project and use the generated file:

```bash
# Create new project
npx react-native init MyApp

# Copy generated file
cp myapp_mobile.js MyApp/App.js

# Run on iOS
cd MyApp && npx react-native run-ios

# Run on Android
cd MyApp && npx react-native run-android
```

## Component Mapping

Quantum UI components map to React Native components:

| Quantum Component | React Native Component |
|-------------------|----------------------|
| `ui:window` | `SafeAreaView` + `View` |
| `ui:hbox` | `View` (flexDirection: 'row') |
| `ui:vbox` | `View` (flexDirection: 'column') |
| `ui:text` | `Text` |
| `ui:button` | `TouchableOpacity` |
| `ui:input` | `TextInput` |
| `ui:checkbox` | `TouchableOpacity` (custom) |
| `ui:switch` | `Switch` |
| `ui:select` | `Picker` or custom |
| `ui:image` | `Image` |
| `ui:list` | `FlatList` |
| `ui:scrollbox` | `ScrollView` |
| `ui:loading` | `ActivityIndicator` |
| `ui:progress` | Custom `View` |
| `ui:tabs` | Custom with state |
| `ui:modal` | `Modal` |

## Generated Code Structure

### Imports

```javascript
import React, { useState, useCallback } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  TouchableOpacity,
  TextInput,
  Switch,
  FlatList,
  ScrollView,
  Image,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
```

### App Component

```javascript
export default function App() {
  // State declarations from q:set
  const [count, setCount] = useState(0);
  const [userName, setUserName] = useState('');

  // Function handlers from q:function
  const increment = useCallback(() => {
    setCount(count + 1);
  }, [count]);

  const decrement = useCallback(() => {
    setCount(count - 1);
  }, [count]);

  // JSX content from UI components
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.vbox}>
        <Text style={styles.text}>{count}</Text>
        <TouchableOpacity style={styles.button} onPress={increment}>
          <Text style={styles.buttonText}>+1</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}
```

### StyleSheet

```javascript
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  vbox: {
    flexDirection: 'column',
    padding: 24,
    gap: 16,
  },
  hbox: {
    flexDirection: 'row',
    gap: 8,
  },
  text: {
    fontSize: 16,
    color: '#1e293b',
  },
  textBold: {
    fontWeight: 'bold',
  },
  button: {
    backgroundColor: '#3b82f6',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 6,
    alignItems: 'center',
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 6,
    padding: 12,
    fontSize: 16,
  },
  // ... more styles
});
```

## State Management

### useState Hooks

Each `q:set` variable becomes a useState hook:

```xml
<q:set name="count" value="0" type="number" />
<q:set name="isEnabled" value="true" type="boolean" />
<q:set name="items" value="[]" type="array" />
```

Generated:

```javascript
const [count, setCount] = useState(0);
const [isEnabled, setIsEnabled] = useState(true);
const [items, setItems] = useState([]);
```

### Event Handlers with useCallback

Functions are wrapped in useCallback for optimization:

```xml
<q:function name="toggleEnabled">
  <q:set name="isEnabled" value="{!isEnabled}" />
</q:function>
```

Generated:

```javascript
const toggleEnabled = useCallback(() => {
  setIsEnabled(!isEnabled);
}, [isEnabled]);
```

### Two-Way Binding

Input binding uses onChangeText:

```xml
<ui:input bind="userName" placeholder="Enter name" />
```

Generated:

```javascript
<TextInput
  style={styles.input}
  value={userName}
  onChangeText={setUserName}
  placeholder="Enter name"
/>
```

## Layout and Styling

### Flexbox Layouts

Quantum layouts translate to React Native flexbox:

```xml
<ui:hbox gap="md" align="center" justify="between">
  <ui:text>Left</ui:text>
  <ui:text>Right</ui:text>
</ui:hbox>
```

Generated:

```javascript
<View style={[styles.hbox, { gap: 16, alignItems: 'center', justifyContent: 'space-between' }]}>
  <Text style={styles.text}>Left</Text>
  <Text style={styles.text}>Right</Text>
</View>
```

### Design Token Translation

| Token | React Native Value |
|-------|-------------------|
| `xs` | 4 |
| `sm` | 8 |
| `md` | 16 |
| `lg` | 24 |
| `xl` | 32 |
| `2xl` | 48 |

### Dynamic Styles

Layout attributes generate dynamic style objects:

```xml
<ui:vbox padding="lg" background="light" width="fill">
```

Generated:

```javascript
<View style={[styles.vbox, styles.dyn_1]}>

// In StyleSheet
dyn_1: {
  padding: 24,
  backgroundColor: '#f8fafc',
  flex: 1,
}
```

## Complex Components

### Tabs

Tab panels require state management:

```xml
<ui:tabs>
  <ui:tab title="Tab 1">Content 1</ui:tab>
  <ui:tab title="Tab 2">Content 2</ui:tab>
</ui:tabs>
```

Generated:

```javascript
const [activeTab_1, setActiveTab_1] = useState(0);

// In JSX
<View>
  {/* Tab headers */}
  <View style={styles.tabHeader}>
    <TouchableOpacity
      style={[styles.tabButton, activeTab_1 === 0 && styles.tabButtonActive]}
      onPress={() => setActiveTab_1(0)}
    >
      <Text style={[styles.tabButtonText, activeTab_1 === 0 && styles.tabButtonTextActive]}>
        Tab 1
      </Text>
    </TouchableOpacity>
    <TouchableOpacity
      style={[styles.tabButton, activeTab_1 === 1 && styles.tabButtonActive]}
      onPress={() => setActiveTab_1(1)}
    >
      <Text>Tab 2</Text>
    </TouchableOpacity>
  </View>

  {/* Tab contents */}
  {activeTab_1 === 0 && (
    <View style={styles.tabContent}>
      <Text>Content 1</Text>
    </View>
  )}
  {activeTab_1 === 1 && (
    <View style={styles.tabContent}>
      <Text>Content 2</Text>
    </View>
  )}
</View>
```

### Accordion Sections

```xml
<ui:accordion>
  <ui:section title="Section 1" expanded="true">
    Content 1
  </ui:section>
  <ui:section title="Section 2">
    Content 2
  </ui:section>
</ui:accordion>
```

Generated with expandable state for each section.

### Lists with Data

```xml
<ui:list source="{items}">
  <ui:item>{item.name}</ui:item>
</ui:list>
```

Generated:

```javascript
<FlatList
  data={items}
  renderItem={({item}) => (
    <View style={styles.listItem}>
      <Text>{item.name}</Text>
    </View>
  )}
  keyExtractor={(item, index) => index.toString()}
/>
```

## Input Types

### Text Input

```xml
<ui:input bind="email" type="email" placeholder="Email" />
```

```javascript
<TextInput
  style={styles.input}
  value={email}
  onChangeText={setEmail}
  placeholder="Email"
  keyboardType="email-address"
  autoCapitalize="none"
/>
```

### Password Input

```xml
<ui:input bind="password" type="password" />
```

```javascript
<TextInput
  style={styles.input}
  value={password}
  onChangeText={setPassword}
  secureTextEntry={true}
/>
```

### Number Input

```xml
<ui:input bind="age" type="number" />
```

```javascript
<TextInput
  style={styles.input}
  value={age}
  onChangeText={setAge}
  keyboardType="numeric"
/>
```

## Building for iOS/Android

### iOS

```bash
cd MyApp

# Install pods
cd ios && pod install && cd ..

# Run on simulator
npx react-native run-ios

# Run on device
npx react-native run-ios --device "My iPhone"

# Build for release
cd ios && xcodebuild -workspace MyApp.xcworkspace -scheme MyApp -configuration Release
```

### Android

```bash
cd MyApp

# Run on emulator
npx react-native run-android

# Run on device
npx react-native run-android --deviceId <device_id>

# Build APK for release
cd android && ./gradlew assembleRelease
```

### Expo (Alternative)

For easier development without native setup:

```bash
# Create Expo project
npx create-expo-app MyApp

# Copy generated code
cp myapp_mobile.js MyApp/App.js

# Start development
cd MyApp && npx expo start
```

## Example: Task Manager

### Quantum Source

```xml
<q:application id="tasks" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <q:set name="tasks" value="[]" type="array" />
  <q:set name="newTask" value="" />

  <q:function name="addTask">
    <q:if condition="newTask != ''">
      <q:set name="tasks" operation="append" value="{newTask}" />
      <q:set name="newTask" value="" />
    </q:if>
  </q:function>

  <ui:window title="Task Manager">
    <ui:vbox padding="lg" gap="md">
      <ui:text size="2xl" weight="bold">My Tasks</ui:text>

      <ui:hbox gap="sm">
        <ui:input bind="newTask" placeholder="New task..." width="fill" />
        <ui:button on-click="addTask" variant="primary">Add</ui:button>
      </ui:hbox>

      <ui:list source="{tasks}">
        <ui:item>
          <ui:text>{item}</ui:text>
        </ui:item>
      </ui:list>
    </ui:vbox>
  </ui:window>

</q:application>
```

### Generated React Native

```javascript
import React, { useState, useCallback } from 'react';
import {
  SafeAreaView,
  View,
  Text,
  TouchableOpacity,
  TextInput,
  FlatList,
  StyleSheet,
} from 'react-native';

export default function App() {
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState('');

  const addTask = useCallback(() => {
    if (newTask !== '') {
      setTasks([...tasks, newTask]);
      setNewTask('');
    }
  }, [tasks, newTask]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={[styles.vbox, { padding: 24, gap: 16 }]}>
        <Text style={[styles.text, { fontSize: 32, fontWeight: 'bold' }]}>
          My Tasks
        </Text>

        <View style={[styles.hbox, { gap: 8 }]}>
          <TextInput
            style={[styles.input, { flex: 1 }]}
            value={newTask}
            onChangeText={setNewTask}
            placeholder="New task..."
          />
          <TouchableOpacity style={styles.button} onPress={addTask}>
            <Text style={styles.buttonText}>Add</Text>
          </TouchableOpacity>
        </View>

        <FlatList
          data={tasks}
          renderItem={({item}) => (
            <View style={styles.listItem}>
              <Text style={styles.text}>{item}</Text>
            </View>
          )}
          keyExtractor={(item, index) => index.toString()}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  vbox: {
    flexDirection: 'column',
  },
  hbox: {
    flexDirection: 'row',
  },
  text: {
    fontSize: 16,
    color: '#1e293b',
  },
  button: {
    backgroundColor: '#3b82f6',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 6,
    alignItems: 'center',
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 6,
    padding: 12,
    fontSize: 16,
  },
  listItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
});
```

## Limitations

Some features have limited support in React Native:

| Feature | Limitation |
|---------|------------|
| `ui:chart` | Requires additional library (react-native-chart-kit) |
| `ui:markdown` | Requires additional library (react-native-markdown-display) |
| `ui:modal` | Uses React Native Modal component |
| External links | Requires Linking API |
| Complex animations | Use Animated API or Reanimated |
| Web-specific CSS | Not all CSS properties are supported |

## Best Practices

1. **Test on both platforms** - iOS and Android may render differently
2. **Use flex layouts** - More reliable than fixed sizes
3. **Handle keyboard** - Use KeyboardAvoidingView for forms
4. **Optimize lists** - Use FlatList for large datasets
5. **Platform-specific code** - Use Platform.OS when needed

## Related

- [HTML Target](/targets/html) - Web output
- [Desktop Target](/targets/desktop) - Native desktop apps
- [Terminal Target](/targets/terminal) - TUI applications
- [React Native Documentation](https://reactnative.dev/)

/**
 * AI Prompt Templates
 *
 * Contains all prompts used for AI-assisted features.
 */

/**
 * Error explanation prompt
 */
export function getErrorExplanationPrompt(context: {
    errorMessage: string;
    surroundingCode: string;
    tagContext: string;
    documentPath: string;
}): string {
    return `You are an expert in the Quantum Framework, an XML-based declarative web framework.

A user has encountered an error and needs help understanding it.

**Error Message:**
${context.errorMessage}

**Tag Context:**
${context.tagContext}

**Code Around Error (>>> marks the error line):**
\`\`\`xml
${context.surroundingCode}
\`\`\`

**File:**
${context.documentPath}

Please explain:
1. What this error means in plain language
2. Why it might have occurred
3. How to fix it with a specific code example

Use clear, concise language. Format code examples with triple backticks.

**Quantum Framework Reference:**
- Tags use the \`q:\` prefix (e.g., \`<q:set>\`, \`<q:if>\`, \`<q:loop>\`)
- Variables are set with: \`<q:set var="name" value="value"/>\`
- Databinding uses curly braces: \`{variableName}\`
- Components require a name: \`<q:component name="MyComponent">\`
- Conditionals: \`<q:if test="condition">\`
- Loops: \`<q:loop array="{items}" item="item">\` or \`<q:loop from="1" to="10" index="i">\`
- Functions: \`<q:function name="myFunc" params="param1, param2">\``;
}

/**
 * Fix suggestion prompt
 */
export function getSuggestFixPrompt(context: {
    errorMessage: string;
    code: string;
    fileName: string;
}): string {
    return `You are an expert in the Quantum Framework, an XML-based declarative web framework.

A user needs help fixing an error in their code.

**Error Message:**
${context.errorMessage}

**Code (>>> marks the error line):**
\`\`\`xml
${context.code}
\`\`\`

**File:**
${context.fileName}

Please provide:
1. A brief explanation of the issue (1-2 sentences)
2. The corrected code in a code block

IMPORTANT: Only output the fixed line(s), not the entire file. Keep your response concise.

**Quantum Framework Reference:**
- Tags use the \`q:\` prefix
- Required attributes vary by tag:
  - \`q:component\`: name
  - \`q:set\`: var, value
  - \`q:if\`: test
  - \`q:loop\`: (array + item) OR (from + to + index)
  - \`q:function\`: name
  - \`q:query\`: name, datasource
  - \`q:include\`: src
- All tags must be properly closed or self-closing`;
}

/**
 * Documentation lookup prompt
 */
export function getDocumentationPrompt(context: {
    tagName: string;
    attributes: string[];
    currentCode?: string;
}): string {
    return `You are an expert in the Quantum Framework.

Provide documentation for the following Quantum tag:

**Tag:** \`${context.tagName}\`
**Current Attributes:** ${context.attributes.length > 0 ? context.attributes.join(', ') : 'None'}
${context.currentCode ? `**Current Usage:**\n\`\`\`xml\n${context.currentCode}\n\`\`\`` : ''}

Please provide:
1. **Purpose**: What this tag does (1-2 sentences)
2. **Required Attributes**: List with descriptions
3. **Optional Attributes**: List with descriptions
4. **Example**: A practical code example
5. **Common Patterns**: Any common usage patterns or best practices

Format the response in Markdown.`;
}

/**
 * Code completion prompt (for complex completions)
 */
export function getCodeCompletionPrompt(context: {
    beforeCursor: string;
    afterCursor: string;
    fileName: string;
}): string {
    return `You are an expert in the Quantum Framework, an XML-based declarative web framework.

Complete the following code. The cursor position is marked with |CURSOR|.

**Code:**
\`\`\`xml
${context.beforeCursor}|CURSOR|${context.afterCursor}
\`\`\`

**File:** ${context.fileName}

Provide ONLY the completion text that should be inserted at the cursor position.
Do not include any explanation or the surrounding code.
Keep the completion concise and contextually appropriate.`;
}

/**
 * Refactoring suggestion prompt
 */
export function getRefactoringPrompt(context: {
    code: string;
    refactoringType: 'extract-component' | 'extract-function' | 'simplify' | 'optimize';
}): string {
    const refactoringDescriptions: Record<string, string> = {
        'extract-component': 'Extract the selected code into a reusable component',
        'extract-function': 'Extract the selected code into a function',
        'simplify': 'Simplify the code while maintaining the same functionality',
        'optimize': 'Optimize the code for better performance'
    };

    return `You are an expert in the Quantum Framework.

**Task:** ${refactoringDescriptions[context.refactoringType]}

**Original Code:**
\`\`\`xml
${context.code}
\`\`\`

Please provide:
1. The refactored code in a code block
2. A brief explanation of the changes made

**Quantum Best Practices:**
- Use components for reusable UI elements
- Use functions for reusable logic
- Keep components focused and single-purpose
- Use meaningful names for variables and functions
- Prefer declarative patterns over imperative ones`;
}

/**
 * Generate component prompt
 */
export function getGenerateComponentPrompt(context: {
    description: string;
    name?: string;
}): string {
    return `You are an expert in the Quantum Framework.

Generate a Quantum component based on this description:

**Description:** ${context.description}
${context.name ? `**Component Name:** ${context.name}` : ''}

Please generate:
1. A complete, working Quantum component
2. Include appropriate variables, functions, and UI elements
3. Add comments explaining key parts

**Quantum Component Structure:**
\`\`\`xml
<q:component name="ComponentName">
    <!-- Variables -->
    <q:set var="..." value="..."/>

    <!-- Functions (optional) -->
    <q:function name="...">
        ...
    </q:function>

    <!-- UI -->
    <div>
        ...
    </div>
</q:component>
\`\`\`

Generate clean, well-structured code following Quantum best practices.`;
}

/**
 * Query builder prompt
 */
export function getQueryBuilderPrompt(context: {
    tables: string[];
    description: string;
}): string {
    return `You are an expert in the Quantum Framework and SQL.

Generate a Quantum query based on this description:

**Available Tables:** ${context.tables.join(', ')}
**Description:** ${context.description}

Please generate:
1. A \`<q:query>\` tag with the appropriate SQL
2. Show how to loop through and display the results

**Quantum Query Syntax:**
\`\`\`xml
<q:query name="queryName" datasource="default">
    SELECT columns FROM table WHERE conditions
</q:query>

<q:loop array="{queryName}" item="row">
    <div>{row.column}</div>
</q:loop>
\`\`\`

Generate the query with proper parameterization if user input is involved.`;
}

/**
 * Debug assistance prompt
 */
export function getDebugAssistancePrompt(context: {
    code: string;
    variables: Record<string, unknown>;
    error?: string;
    expectedBehavior: string;
    actualBehavior: string;
}): string {
    return `You are an expert in the Quantum Framework debugging.

Help debug this issue:

**Code:**
\`\`\`xml
${context.code}
\`\`\`

**Current Variable Values:**
\`\`\`json
${JSON.stringify(context.variables, null, 2)}
\`\`\`

${context.error ? `**Error:** ${context.error}\n` : ''}
**Expected Behavior:** ${context.expectedBehavior}
**Actual Behavior:** ${context.actualBehavior}

Please:
1. Identify the likely cause of the issue
2. Explain why this is happening
3. Provide a fix with code example
4. Suggest how to prevent similar issues`;
}

"""
Quantum Admin - Jenkins Pipeline Abstraction
Parse <q:pipeline> XML syntax and generate Jenkinsfiles
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel


# ============================================================================
# Pipeline Models
# ============================================================================

class StepType(str, Enum):
    """Pipeline step types"""
    SHELL = "shell"
    SCRIPT = "script"
    DOCKER = "docker"
    GIT = "git"
    DEPLOY = "deploy"
    TEST = "test"
    BUILD = "build"
    NOTIFY = "notify"


class TriggerType(str, Enum):
    """Pipeline trigger types"""
    CRON = "cron"
    SCM = "scm"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class PipelineStep(BaseModel):
    """Represents a single pipeline step"""
    name: Optional[str] = None
    type: StepType = StepType.SHELL
    command: str
    args: Optional[Dict[str, Any]] = None
    when: Optional[str] = None  # Conditional execution
    timeout: Optional[int] = None  # Timeout in minutes


class PipelineStage(BaseModel):
    """Represents a pipeline stage"""
    name: str
    steps: List[PipelineStep] = []
    parallel: bool = False
    when: Optional[str] = None  # Conditional execution
    environment: Optional[Dict[str, str]] = None


class PipelineTrigger(BaseModel):
    """Pipeline trigger configuration"""
    type: TriggerType
    config: str  # Cron expression or SCM config


class PipelineAgent(BaseModel):
    """Pipeline agent configuration"""
    type: str = "any"  # any, docker, kubernetes, node
    label: Optional[str] = None
    image: Optional[str] = None


class Pipeline(BaseModel):
    """Complete pipeline definition"""
    name: str
    description: Optional[str] = None
    agent: PipelineAgent = PipelineAgent()
    environment: Optional[Dict[str, str]] = None
    parameters: Optional[Dict[str, Any]] = None
    triggers: Optional[List[PipelineTrigger]] = None
    stages: List[PipelineStage] = []
    post_actions: Optional[Dict[str, List[PipelineStep]]] = None  # success, failure, always


# ============================================================================
# XML Parser
# ============================================================================

class QuantumPipelineParser:
    """Parser for <q:pipeline> XML syntax"""

    def __init__(self):
        self.pipeline: Optional[Pipeline] = None

    def parse(self, xml_content: str) -> Pipeline:
        """Parse <q:pipeline> XML and return Pipeline object"""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        if root.tag != "q:pipeline":
            raise ValueError("Root element must be <q:pipeline>")

        # Parse pipeline attributes
        pipeline_name = root.get("name", "Unnamed Pipeline")
        pipeline_description = root.get("description")

        # Parse agent
        agent = self._parse_agent(root.find("q:agent"))

        # Parse environment
        environment = self._parse_environment(root.find("q:environment"))

        # Parse parameters
        parameters = self._parse_parameters(root.find("q:parameters"))

        # Parse triggers
        triggers = self._parse_triggers(root.find("q:triggers"))

        # Parse stages
        stages = []
        for stage_elem in root.findall("q:stage"):
            stage = self._parse_stage(stage_elem)
            stages.append(stage)

        # Parse post actions
        post_actions = self._parse_post_actions(root.find("q:post"))

        self.pipeline = Pipeline(
            name=pipeline_name,
            description=pipeline_description,
            agent=agent,
            environment=environment,
            parameters=parameters,
            triggers=triggers,
            stages=stages,
            post_actions=post_actions
        )

        return self.pipeline

    def _parse_agent(self, agent_elem: Optional[ET.Element]) -> PipelineAgent:
        """Parse <q:agent> element"""
        if agent_elem is None:
            return PipelineAgent()

        agent_type = agent_elem.get("type", "any")
        label = agent_elem.get("label")
        image = agent_elem.get("image")

        return PipelineAgent(type=agent_type, label=label, image=image)

    def _parse_environment(self, env_elem: Optional[ET.Element]) -> Optional[Dict[str, str]]:
        """Parse <q:environment> element"""
        if env_elem is None:
            return None

        environment = {}
        for var_elem in env_elem.findall("q:var"):
            key = var_elem.get("name")
            value = var_elem.text or ""
            if key:
                environment[key] = value

        return environment if environment else None

    def _parse_parameters(self, params_elem: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
        """Parse <q:parameters> element"""
        if params_elem is None:
            return None

        parameters = {}
        for param_elem in params_elem.findall("q:param"):
            name = param_elem.get("name")
            param_type = param_elem.get("type", "string")
            default = param_elem.get("default")
            description = param_elem.get("description")

            if name:
                parameters[name] = {
                    "type": param_type,
                    "default": default,
                    "description": description
                }

        return parameters if parameters else None

    def _parse_triggers(self, triggers_elem: Optional[ET.Element]) -> Optional[List[PipelineTrigger]]:
        """Parse <q:triggers> element"""
        if triggers_elem is None:
            return None

        triggers = []
        for trigger_elem in triggers_elem:
            if trigger_elem.tag == "q:cron":
                triggers.append(PipelineTrigger(
                    type=TriggerType.CRON,
                    config=trigger_elem.text or ""
                ))
            elif trigger_elem.tag == "q:scm":
                triggers.append(PipelineTrigger(
                    type=TriggerType.SCM,
                    config=trigger_elem.get("interval", "* * * * *")
                ))

        return triggers if triggers else None

    def _parse_stage(self, stage_elem: ET.Element) -> PipelineStage:
        """Parse <q:stage> element"""
        stage_name = stage_elem.get("name", "Unnamed Stage")
        parallel = stage_elem.get("parallel", "false").lower() == "true"
        when = stage_elem.get("when")

        # Parse stage environment
        env_elem = stage_elem.find("q:environment")
        environment = self._parse_environment(env_elem)

        # Parse steps
        steps = []
        for step_elem in stage_elem.findall("q:step"):
            step = self._parse_step(step_elem)
            steps.append(step)

        return PipelineStage(
            name=stage_name,
            steps=steps,
            parallel=parallel,
            when=when,
            environment=environment
        )

    def _parse_step(self, step_elem: ET.Element) -> PipelineStep:
        """Parse <q:step> element"""
        step_name = step_elem.get("name")
        step_type = step_elem.get("type", "shell")
        when = step_elem.get("when")
        timeout = step_elem.get("timeout")

        command = step_elem.text or ""

        # Parse step arguments
        args = {}
        for key, value in step_elem.attrib.items():
            if key not in ["name", "type", "when", "timeout"]:
                args[key] = value

        return PipelineStep(
            name=step_name,
            type=StepType(step_type),
            command=command.strip(),
            args=args if args else None,
            when=when,
            timeout=int(timeout) if timeout else None
        )

    def _parse_post_actions(self, post_elem: Optional[ET.Element]) -> Optional[Dict[str, List[PipelineStep]]]:
        """Parse <q:post> element"""
        if post_elem is None:
            return None

        post_actions = {}

        for condition in ["success", "failure", "always", "cleanup"]:
            condition_elem = post_elem.find(f"q:{condition}")
            if condition_elem is not None:
                steps = []
                for step_elem in condition_elem.findall("q:step"):
                    step = self._parse_step(step_elem)
                    steps.append(step)
                if steps:
                    post_actions[condition] = steps

        return post_actions if post_actions else None


# ============================================================================
# Jenkinsfile Generator
# ============================================================================

class JenkinsfileGenerator:
    """Generate Jenkinsfile from Pipeline object"""

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.indent_level = 0

    def generate(self) -> str:
        """Generate Jenkinsfile content"""
        lines = []

        lines.append("pipeline {")
        self.indent_level += 1

        # Agent
        lines.extend(self._generate_agent())

        # Environment
        if self.pipeline.environment:
            lines.extend(self._generate_environment(self.pipeline.environment))

        # Parameters
        if self.pipeline.parameters:
            lines.extend(self._generate_parameters())

        # Triggers
        if self.pipeline.triggers:
            lines.extend(self._generate_triggers())

        # Stages
        lines.extend(self._generate_stages())

        # Post actions
        if self.pipeline.post_actions:
            lines.extend(self._generate_post_actions())

        self.indent_level -= 1
        lines.append("}")

        return "\n".join(lines)

    def _indent(self, text: str = "") -> str:
        """Add indentation to text"""
        return "    " * self.indent_level + text

    def _generate_agent(self) -> List[str]:
        """Generate agent block"""
        lines = []
        agent = self.pipeline.agent

        if agent.type == "any":
            lines.append(self._indent("agent any"))
        elif agent.type == "docker":
            lines.append(self._indent("agent {"))
            self.indent_level += 1
            lines.append(self._indent("docker {"))
            self.indent_level += 1
            lines.append(self._indent(f"image '{agent.image}'"))
            self.indent_level -= 1
            lines.append(self._indent("}"))
            self.indent_level -= 1
            lines.append(self._indent("}"))
        elif agent.type == "node":
            lines.append(self._indent("agent {"))
            self.indent_level += 1
            lines.append(self._indent(f"node {{ label '{agent.label}' }}"))
            self.indent_level -= 1
            lines.append(self._indent("}"))

        return lines

    def _generate_environment(self, environment: Dict[str, str]) -> List[str]:
        """Generate environment block"""
        lines = []
        lines.append(self._indent("environment {"))
        self.indent_level += 1

        for key, value in environment.items():
            lines.append(self._indent(f"{key} = '{value}'"))

        self.indent_level -= 1
        lines.append(self._indent("}"))
        return lines

    def _generate_parameters(self) -> List[str]:
        """Generate parameters block"""
        lines = []
        lines.append(self._indent("parameters {"))
        self.indent_level += 1

        for name, param in self.pipeline.parameters.items():
            param_type = param.get("type", "string")
            default = param.get("default", "")
            description = param.get("description", "")

            if param_type == "string":
                lines.append(self._indent(f"string(name: '{name}', defaultValue: '{default}', description: '{description}')"))
            elif param_type == "boolean":
                lines.append(self._indent(f"booleanParam(name: '{name}', defaultValue: {default.lower()}, description: '{description}')"))
            elif param_type == "choice":
                choices = param.get("choices", [])
                lines.append(self._indent(f"choice(name: '{name}', choices: {choices}, description: '{description}')"))

        self.indent_level -= 1
        lines.append(self._indent("}"))
        return lines

    def _generate_triggers(self) -> List[str]:
        """Generate triggers block"""
        lines = []
        lines.append(self._indent("triggers {"))
        self.indent_level += 1

        for trigger in self.pipeline.triggers:
            if trigger.type == TriggerType.CRON:
                lines.append(self._indent(f"cron('{trigger.config}')"))
            elif trigger.type == TriggerType.SCM:
                lines.append(self._indent(f"pollSCM('{trigger.config}')"))

        self.indent_level -= 1
        lines.append(self._indent("}"))
        return lines

    def _generate_stages(self) -> List[str]:
        """Generate stages block"""
        lines = []
        lines.append(self._indent("stages {"))
        self.indent_level += 1

        for stage in self.pipeline.stages:
            lines.extend(self._generate_stage(stage))

        self.indent_level -= 1
        lines.append(self._indent("}"))
        return lines

    def _generate_stage(self, stage: PipelineStage) -> List[str]:
        """Generate a single stage"""
        lines = []
        lines.append(self._indent(f"stage('{stage.name}') {{"))
        self.indent_level += 1

        # When condition
        if stage.when:
            lines.append(self._indent(f"when {{ {stage.when} }}"))

        # Environment
        if stage.environment:
            lines.extend(self._generate_environment(stage.environment))

        # Steps
        if stage.parallel:
            lines.append(self._indent("parallel {"))
            self.indent_level += 1
            for i, step in enumerate(stage.steps):
                lines.append(self._indent(f"stage('Parallel {i+1}') {{"))
                self.indent_level += 1
                lines.append(self._indent("steps {"))
                self.indent_level += 1
                lines.extend(self._generate_step(step))
                self.indent_level -= 1
                lines.append(self._indent("}"))
                self.indent_level -= 1
                lines.append(self._indent("}"))
            self.indent_level -= 1
            lines.append(self._indent("}"))
        else:
            lines.append(self._indent("steps {"))
            self.indent_level += 1
            for step in stage.steps:
                lines.extend(self._generate_step(step))
            self.indent_level -= 1
            lines.append(self._indent("}"))

        self.indent_level -= 1
        lines.append(self._indent("}"))
        return lines

    def _generate_step(self, step: PipelineStep) -> List[str]:
        """Generate a single step"""
        lines = []

        # Handle timeout
        if step.timeout:
            lines.append(self._indent(f"timeout(time: {step.timeout}, unit: 'MINUTES') {{"))
            self.indent_level += 1

        # Generate step based on type
        if step.type == StepType.SHELL:
            lines.append(self._indent(f"sh '''{step.command}'''"))
        elif step.type == StepType.SCRIPT:
            lines.append(self._indent("script {"))
            self.indent_level += 1
            for line in step.command.split("\n"):
                lines.append(self._indent(line))
            self.indent_level -= 1
            lines.append(self._indent("}"))
        elif step.type == StepType.GIT:
            url = step.args.get("url") if step.args else ""
            branch = step.args.get("branch", "main") if step.args else "main"
            lines.append(self._indent(f"git url: '{url}', branch: '{branch}'"))
        elif step.type == StepType.DOCKER:
            image = step.args.get("image") if step.args else ""
            lines.append(self._indent(f"docker.image('{image}').inside {{"))
            self.indent_level += 1
            lines.append(self._indent(f"sh '''{step.command}'''"))
            self.indent_level -= 1
            lines.append(self._indent("}"))

        # Close timeout block
        if step.timeout:
            self.indent_level -= 1
            lines.append(self._indent("}"))

        return lines

    def _generate_post_actions(self) -> List[str]:
        """Generate post actions block"""
        lines = []
        lines.append(self._indent("post {"))
        self.indent_level += 1

        for condition, steps in self.pipeline.post_actions.items():
            lines.append(self._indent(f"{condition} {{"))
            self.indent_level += 1
            for step in steps:
                lines.extend(self._generate_step(step))
            self.indent_level -= 1
            lines.append(self._indent("}"))

        self.indent_level -= 1
        lines.append(self._indent("}"))
        return lines


# ============================================================================
# Template Library
# ============================================================================

PIPELINE_TEMPLATES = {
    "basic-build": """<q:pipeline name="Basic Build Pipeline" description="Simple build and test pipeline">
    <q:agent type="any"/>

    <q:stage name="Checkout">
        <q:step type="git" url="https://github.com/user/repo.git" branch="main"/>
    </q:stage>

    <q:stage name="Build">
        <q:step type="shell">npm install</q:step>
        <q:step type="shell">npm run build</q:step>
    </q:stage>

    <q:stage name="Test">
        <q:step type="shell">npm test</q:step>
    </q:stage>

    <q:post>
        <q:success>
            <q:step type="shell">echo "Build successful!"</q:step>
        </q:success>
        <q:failure>
            <q:step type="shell">echo "Build failed!"</q:step>
        </q:failure>
    </q:post>
</q:pipeline>""",

    "docker-deploy": """<q:pipeline name="Docker Deploy Pipeline" description="Build and deploy Docker image">
    <q:agent type="docker" image="docker:latest"/>

    <q:environment>
        <q:var name="DOCKER_REGISTRY">registry.example.com</q:var>
        <q:var name="IMAGE_NAME">myapp</q:var>
    </q:environment>

    <q:stage name="Build Image">
        <q:step type="shell">docker build -t $IMAGE_NAME:$BUILD_NUMBER .</q:step>
    </q:stage>

    <q:stage name="Push Image">
        <q:step type="shell">docker tag $IMAGE_NAME:$BUILD_NUMBER $DOCKER_REGISTRY/$IMAGE_NAME:latest</q:step>
        <q:step type="shell">docker push $DOCKER_REGISTRY/$IMAGE_NAME:latest</q:step>
    </q:stage>

    <q:stage name="Deploy">
        <q:step type="shell">kubectl set image deployment/myapp myapp=$DOCKER_REGISTRY/$IMAGE_NAME:latest</q:step>
    </q:stage>
</q:pipeline>""",

    "parallel-tests": """<q:pipeline name="Parallel Test Pipeline" description="Run tests in parallel">
    <q:agent type="any"/>

    <q:stage name="Parallel Tests" parallel="true">
        <q:step type="shell" name="Unit Tests">npm run test:unit</q:step>
        <q:step type="shell" name="Integration Tests">npm run test:integration</q:step>
        <q:step type="shell" name="E2E Tests">npm run test:e2e</q:step>
    </q:stage>
</q:pipeline>"""
}


# ============================================================================
# Utility Functions
# ============================================================================

def parse_qpipeline(xml_content: str) -> Pipeline:
    """Parse <q:pipeline> XML content"""
    parser = QuantumPipelineParser()
    return parser.parse(xml_content)


def generate_jenkinsfile(pipeline: Pipeline) -> str:
    """Generate Jenkinsfile from Pipeline object"""
    generator = JenkinsfileGenerator(pipeline)
    return generator.generate()


def qpipeline_to_jenkinsfile(xml_content: str) -> str:
    """Convert <q:pipeline> XML directly to Jenkinsfile"""
    pipeline = parse_qpipeline(xml_content)
    return generate_jenkinsfile(pipeline)

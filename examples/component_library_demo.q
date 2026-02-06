<q:application id="component-demo" type="ui">
    <ui:window title="Component Library Demo">
        <ui:header title="Quantum UI Component Library" />

        <ui:vbox padding="16" gap="24">
            <!-- Card Demo -->
            <ui:panel title="Card Component">
                <ui:hbox gap="16">
                    <ui:card title="Basic Card" subtitle="A simple card" width="300">
                        <ui:card-body>
                            <ui:text>Card content goes here. Cards are versatile containers for content.</ui:text>
                        </ui:card-body>
                        <ui:card-footer>
                            <ui:button variant="primary">Action</ui:button>
                        </ui:card-footer>
                    </ui:card>

                    <ui:card title="Elevated Card" variant="elevated" width="300">
                        <ui:card-body>
                            <ui:text>This card has an elevated shadow effect.</ui:text>
                        </ui:card-body>
                    </ui:card>
                </ui:hbox>
            </ui:panel>

            <!-- Avatar Demo -->
            <ui:panel title="Avatar Component">
                <ui:hbox gap="16" align="center">
                    <ui:avatar name="John Doe" size="xs" />
                    <ui:avatar name="Jane Smith" size="sm" />
                    <ui:avatar name="Bob Wilson" size="md" status="online" />
                    <ui:avatar name="Alice Brown" size="lg" status="away" />
                    <ui:avatar src="/user.jpg" size="xl" status="busy" />
                    <ui:avatar name="Square" shape="square" />
                </ui:hbox>
            </ui:panel>

            <!-- Alert Demo -->
            <ui:panel title="Alert Component">
                <ui:vbox gap="8">
                    <ui:alert variant="info" title="Information">This is an informational message.</ui:alert>
                    <ui:alert variant="success" title="Success" dismissible="true">Operation completed successfully!</ui:alert>
                    <ui:alert variant="warning" title="Warning">Please review before proceeding.</ui:alert>
                    <ui:alert variant="danger" title="Error" dismissible="true">An error occurred.</ui:alert>
                </ui:vbox>
            </ui:panel>

            <!-- Tooltip Demo -->
            <ui:panel title="Tooltip Component">
                <ui:hbox gap="24" padding="16">
                    <ui:tooltip content="This is a top tooltip" position="top">
                        <ui:button>Hover (Top)</ui:button>
                    </ui:tooltip>
                    <ui:tooltip content="This is a bottom tooltip" position="bottom">
                        <ui:button>Hover (Bottom)</ui:button>
                    </ui:tooltip>
                    <ui:tooltip content="This is a left tooltip" position="left">
                        <ui:button>Hover (Left)</ui:button>
                    </ui:tooltip>
                    <ui:tooltip content="This is a right tooltip" position="right">
                        <ui:button>Hover (Right)</ui:button>
                    </ui:tooltip>
                </ui:hbox>
            </ui:panel>

            <!-- Dropdown Demo -->
            <ui:panel title="Dropdown Component">
                <ui:hbox gap="16">
                    <ui:dropdown label="Click Menu">
                        <ui:option value="edit" label="Edit" />
                        <ui:option value="duplicate" label="Duplicate" />
                        <ui:option value="delete" label="Delete" />
                    </ui:dropdown>

                    <ui:dropdown label="Hover Menu" trigger="hover">
                        <ui:option value="profile" label="Profile" />
                        <ui:option value="settings" label="Settings" />
                        <ui:option value="logout" label="Log out" />
                    </ui:dropdown>

                    <ui:dropdown label="Right Aligned" align="right">
                        <ui:option value="opt1" label="Option 1" />
                        <ui:option value="opt2" label="Option 2" />
                    </ui:dropdown>
                </ui:hbox>
            </ui:panel>

            <!-- Breadcrumb Demo -->
            <ui:panel title="Breadcrumb Component">
                <ui:breadcrumb>
                    <ui:breadcrumb-item label="Home" to="/" />
                    <ui:breadcrumb-item label="Products" to="/products" />
                    <ui:breadcrumb-item label="Electronics" to="/products/electronics" />
                    <ui:breadcrumb-item label="Smartphones" />
                </ui:breadcrumb>

                <ui:breadcrumb separator=">">
                    <ui:breadcrumb-item label="Dashboard" to="/dashboard" />
                    <ui:breadcrumb-item label="Reports" to="/reports" />
                    <ui:breadcrumb-item label="Annual" />
                </ui:breadcrumb>
            </ui:panel>

            <!-- Chart Demo -->
            <ui:panel title="Chart Component">
                <ui:chart
                    type="bar"
                    title="Monthly Sales"
                    labels="Jan,Feb,Mar,Apr,May"
                    values="120,200,150,280,310"
                    colors="#3b82f6,#22c55e,#f59e0b,#ef4444,#8b5cf6"
                />
            </ui:panel>

            <!-- Pagination Demo -->
            <ui:panel title="Pagination Component">
                <ui:vbox gap="16">
                    <ui:pagination total="100" page-size="10" current="3" />
                    <ui:pagination total="500" show-total="true" show-jump="true" />
                </ui:vbox>
            </ui:panel>

            <!-- Skeleton Demo -->
            <ui:panel title="Skeleton Loading Component">
                <ui:hbox gap="24">
                    <ui:vbox gap="8" width="200">
                        <ui:text weight="bold">Text Skeleton</ui:text>
                        <ui:skeleton variant="text" lines="3" />
                    </ui:vbox>

                    <ui:vbox gap="8">
                        <ui:text weight="bold">Circle Skeleton</ui:text>
                        <ui:skeleton variant="circle" />
                    </ui:vbox>

                    <ui:vbox gap="8" width="200">
                        <ui:text weight="bold">Card Skeleton</ui:text>
                        <ui:skeleton variant="card" />
                    </ui:vbox>
                </ui:hbox>
            </ui:panel>

            <!-- Modal Demo (button to trigger) -->
            <ui:panel title="Modal Component">
                <ui:button onclick="document.getElementById('demo-modal').classList.add('q-modal-open')">
                    Open Modal
                </ui:button>
            </ui:panel>
        </ui:vbox>

        <!-- Modal (hidden by default) -->
        <ui:modal modal-id="demo-modal" title="Example Modal" size="md">
            <ui:text>This is the modal content. You can put any UI components here.</ui:text>
            <ui:vbox gap="8" padding="16">
                <ui:formitem label="Name">
                    <ui:input placeholder="Enter your name" />
                </ui:formitem>
                <ui:formitem label="Email">
                    <ui:input type="email" placeholder="Enter your email" />
                </ui:formitem>
            </ui:vbox>
        </ui:modal>

        <ui:footer>Quantum UI Component Library v1.0</ui:footer>
    </ui:window>
</q:application>

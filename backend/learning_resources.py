"""Reviewed learning links, shared by role and job-specific roadmaps.

No model-generated URLs or runtime web requests. Extend the exact-name groups
when adding skills; unknown labels get explicitly marked search links. Only the
skill label is placed in a search URL, never a resume, user ID or job description.
"""

from urllib.parse import urlencode, urlsplit

from matching import normalize_skill_name


# Skill aliases in a group share a relevant learning path. Broad paths are
# labelled by their actual subject rather than pretending to be narrow tutorials.
ROADMAP_GROUPS = (
    ('Python|Python Automation', 'python', 'Python'),
    ('Java', 'java', 'Java'),
    ('JavaScript|JavaScript (ES6+)', 'javascript', 'JavaScript'),
    ('TypeScript', 'typescript', 'TypeScript'),
    ('C++', 'cpp', 'C++'),
    ('C#|.NET|ASP.NET', 'aspnet-core', 'ASP.NET Core'),
    ('Go programming', 'golang', 'Go'),
    ('Ruby', 'ruby', 'Ruby'),
    ('PHP', 'php', 'PHP'),
    ('Rust', 'rust', 'Rust'),
    ('Kotlin|Coroutines & Flow', 'kotlin', 'Kotlin'),
    ('Swift|SwiftUI|Async/Await', 'swift-ui', 'Swift and SwiftUI'),
    ('Scala', 'scala', 'Scala'),
    ('Bash|Bash & Terminal', 'shell-bash', 'Shell and Bash'),
    ('Linux|Linux CLI', 'linux', 'Linux'),
    ('HTML', 'html', 'HTML'),
    ('CSS', 'css', 'CSS'),
    ('React', 'react', 'React'),
    ('React Native', 'react-native', 'React Native'),
    ('Angular', 'angular', 'Angular'),
    ('Vue.js', 'vue', 'Vue'),
    ('Next.js', 'nextjs', 'Next.js'),
    ('Node.js|Express.js|npm', 'nodejs', 'Node.js'),
    ('Django', 'django', 'Django'),
    ('Spring|Spring Boot|Hibernate|JPA', 'spring-boot', 'Spring Boot'),
    ('Flutter|Dart', 'flutter', 'Flutter'),
    ('Android|Android Fundamentals|Activities & Fragments|Jetpack Compose|Room Database|Retrofit (HTTP)|Firebase|Google Play', 'android', 'Android'),
    ('iOS|Objective-C|Xcode|Combine|Core Data|URLSession|Swift Package Manager|App Store Connect|Fastlane', 'ios', 'iOS'),
    ('SQL|PL/SQL|SQL Server|MySQL|Oracle|SQLite|Stored Procedures', 'sql', 'SQL'),
    ('PostgreSQL', 'postgresql-dba', 'PostgreSQL'),
    ('MongoDB|NoSQL', 'mongodb', 'MongoDB'),
    ('Redis|Caching (Redis)', 'redis', 'Redis'),
    ('Elasticsearch|ELK Stack', 'elasticsearch', 'Elasticsearch'),
    ('Docker', 'docker', 'Docker'),
    ('Kubernetes|Kubernetes Networking|Helm', 'kubernetes', 'Kubernetes'),
    ('AWS|AWS S3|AWS Networking|Cost Optimization', 'aws', 'AWS'),
    ('Terraform', 'terraform', 'Terraform'),
    ('Git|GitHub|Git & DVC', 'git-github', 'Git and GitHub'),
    ('Ansible|GitHub Actions|GitLab|Jenkins|CircleCI|Travis CI|CI/CD|ArgoCD|Prometheus|Grafana|HashiCorp Vault|Nginx|HAProxy', 'devops', 'DevOps'),
    ('Networking|TCP/IP|OSI Model|Routing & Switching|VLANs & Subnetting|BGP|SDN (OpenFlow)|DNS|Firewalls (iptables)|VPN (OpenVPN)|Grafana (SNMP)', 'network-engineer', 'Network engineering'),
    ('Container Security|Trivy (SAST/SCA)|SOC2 Compliance', 'devsecops', 'DevSecOps'),
    ('Cybersecurity|Network Security|Cryptography|OWASP|OWASP Top 10|Pen Testing|Penetration Testing|Burp Suite|Wireshark|Web Security|Web App Security|Security Testing|Incident Response|Malware Analysis|Threat Intelligence|Threat Modeling|Red Teaming|ISO 27001|Splunk|Splunk (SIEM)', 'cyber-security', 'Cyber security'),
    ('REST APIs|API Testing|Postman & API Testing|HTTP|HTTP Basics|GraphQL|SOAP|gRPC|OAuth|JWT|Auth & JWT|Auth & Security', 'api-design', 'API design'),
    ('System Design|Distributed Systems|Scalability|Microservices', 'system-design', 'System design'),
    ('Design Patterns|SOLID|SOLID Principles|UML|Domain-Driven Design|Event-Driven Arch|Security Architecture|ADRs|MVVM Architecture', 'software-architect', 'Software architecture'),
    ('Object-Oriented Programming|OOP Fundamentals', 'computer-science', 'Computer science'),
    ('Testing Fundamentals|Manual Testing|Agile & SDLC|SDLC|Unit Testing|Integration Testing|Regression Testing|Test Automation|Performance Testing|Playwright|Selenium|Cypress|pytest|JUnit|Testing (JUnit)|Jest|Vitest|TestNG|JMeter|k6|k6 (Performance)|Postman', 'qa', 'Quality assurance'),
    ('Machine Learning|ML Fundamentals|Scikit-learn|Classification Models|Regression Models|Clustering|Model Evaluation|Cross-Validation|Data Preprocessing|Linear Algebra|Neural Networks|Deep Learning|PyTorch|TensorFlow', 'machine-learning', 'Machine learning'),
    ('Analytics Concepts|Data Analysis|Statistics|Statistical Analysis|Descriptive Stats|Pandas|NumPy|NumPy & Pandas|Matplotlib|Data Cleaning|Tableau|Excel', 'data-analyst', 'Data analysis'),
    ('Power BI', 'power-bi', 'Power BI'),
    ('Data Modeling|Data Pipelines|Data Quality|ETL|ETL Concepts|Spark|Airflow|Kafka|Hadoop|Snowflake|BigQuery|dbt', 'data-engineer', 'Data engineering'),
    ('MLOps Concepts|MLflow', 'mlops', 'MLOps'),
    ('AI Agents', 'ai-agents', 'AI agents'),
    ('LLM|LLM Concepts|OpenAI API|Open-Source LLMs|Local LLMs (Ollama)|Embeddings|Vector Databases|RAG|RAG Pipelines|LangChain|Hugging Face|Transformers|NLP', 'ai-engineer', 'AI engineering'),
    ('Tailwind CSS|Vite|Bootstrap|jQuery|AJAX|Web Components', 'frontend', 'Frontend development'),
)

# Primary-source introductions and hands-on guides supplement the visual paths.
GUIDE_GROUPS = (
    ('Python|Python Automation', 'The Python tutorial', 'https://docs.python.org/3/tutorial/'),
    ('Java|Object-Oriented Programming|OOP Fundamentals', 'Learn Java and object-oriented programming', 'https://dev.java/learn/'),
    ('JavaScript|JavaScript (ES6+)', 'MDN JavaScript guide', 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide'),
    ('TypeScript', 'TypeScript handbook', 'https://www.typescriptlang.org/docs/handbook/intro.html'),
    ('C#|.NET|ASP.NET', 'Learn C#', 'https://learn.microsoft.com/en-us/dotnet/csharp/tour-of-csharp/'),
    ('Go programming', 'A Tour of Go', 'https://go.dev/tour/'),
    ('Ruby', 'Ruby in twenty minutes', 'https://www.ruby-lang.org/en/documentation/quickstart/'),
    ('PHP', 'PHP tutorial', 'https://www.php.net/manual/en/tutorial.php'),
    ('Rust', 'The Rust programming language book', 'https://doc.rust-lang.org/book/'),
    ('Kotlin', 'Kotlin getting started', 'https://kotlinlang.org/docs/getting-started.html'),
    ('Coroutines & Flow', 'Kotlin coroutines guide', 'https://kotlinlang.org/docs/coroutines-guide.html'),
    ('Swift|Async/Await', 'The Swift programming language', 'https://docs.swift.org/swift-book/documentation/the-swift-programming-language/'),
    ('Scala', 'Tour of Scala', 'https://docs.scala-lang.org/tour/tour-of-scala.html'),
    ('Bash|Bash & Terminal', 'GNU Bash manual', 'https://www.gnu.org/software/bash/manual/bash.html'),
    ('Linux|Linux CLI', 'Linux command line for beginners', 'https://ubuntu.com/tutorials/command-line-for-beginners'),
    ('PowerShell', 'PowerShell learning resources', 'https://learn.microsoft.com/en-us/powershell/scripting/learn/ps101/00-introduction'),
    ('HTML', 'Learn HTML with MDN', 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content'),
    ('CSS', 'Learn CSS with MDN', 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics'),
    ('React', 'React quick start', 'https://react.dev/learn'),
    ('React Native', 'React Native basics', 'https://reactnative.dev/docs/tutorial'),
    ('Angular', 'Angular tutorials', 'https://angular.dev/tutorials'),
    ('Vue.js', 'Vue tutorial', 'https://vuejs.org/tutorial/'),
    ('Next.js', 'Learn Next.js', 'https://nextjs.org/learn'),
    ('Node.js', 'Introduction to Node.js', 'https://nodejs.org/en/learn/getting-started/introduction-to-nodejs'),
    ('Express.js', 'Express hello world', 'https://expressjs.com/en/starter/hello-world.html'),
    ('npm', 'About npm', 'https://docs.npmjs.com/about-npm'),
    ('Django', 'Write your first Django app', 'https://docs.djangoproject.com/en/stable/intro/tutorial01/'),
    ('Flask', 'Flask tutorial', 'https://flask.palletsprojects.com/en/stable/tutorial/'),
    ('FastAPI', 'FastAPI tutorial', 'https://fastapi.tiangolo.com/tutorial/'),
    ('Spring|Spring Boot', 'Spring getting-started guides', 'https://spring.io/guides'),
    ('Hibernate|JPA', 'Hibernate ORM quick start', 'https://hibernate.org/orm/documentation/'),
    ('Tailwind CSS', 'Tailwind CSS installation and basics', 'https://tailwindcss.com/docs/installation'),
    ('Vite', 'Vite getting started', 'https://vite.dev/guide/'),
    ('Bootstrap', 'Bootstrap introduction', 'https://getbootstrap.com/docs/5.3/getting-started/introduction/'),
    ('jQuery', 'jQuery learning center', 'https://learn.jquery.com/'),
    ('AJAX|HTTP|HTTP Basics', 'MDN HTTP overview', 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview'),
    ('Flutter|Dart', 'Learn Flutter', 'https://docs.flutter.dev/learn'),
    ('Android|Android Fundamentals|Activities & Fragments|Jetpack Compose', 'Android training courses', 'https://developer.android.com/courses'),
    ('Room Database', 'Save data with Room', 'https://developer.android.com/training/data-storage/room'),
    ('Retrofit (HTTP)', 'Retrofit introduction and examples', 'https://github.com/square/retrofit'),
    ('Firebase', 'Firebase documentation', 'https://firebase.google.com/docs'),
    ('Google Play', 'Publish your Android app', 'https://developer.android.com/studio/publish'),
    ('iOS|SwiftUI', 'Apple SwiftUI tutorials', 'https://developer.apple.com/tutorials/swiftui'),
    ('Xcode', 'Xcode documentation', 'https://developer.apple.com/documentation/xcode'),
    ('Combine', 'Combine framework', 'https://developer.apple.com/documentation/combine'),
    ('Core Data', 'Core Data guide', 'https://developer.apple.com/documentation/coredata'),
    ('URLSession', 'URLSession networking', 'https://developer.apple.com/documentation/foundation/urlsession'),
    ('Swift Package Manager', 'Swift package manager guide', 'https://www.swift.org/documentation/package-manager/'),
    ('App Store Connect', 'App Store Connect help', 'https://developer.apple.com/help/app-store-connect/'),
    ('Fastlane', 'Fastlane getting started', 'https://docs.fastlane.tools/'),
    ('SQL|PostgreSQL', 'PostgreSQL and SQL tutorial', 'https://www.postgresql.org/docs/current/tutorial.html'),
    ('SQL Server', 'SQL Server tutorials', 'https://learn.microsoft.com/en-us/sql/sql-server/tutorials-for-sql-server-2016'),
    ('MySQL', 'MySQL tutorial', 'https://dev.mysql.com/doc/refman/8.4/en/tutorial.html'),
    ('SQLite', 'SQLite quick start', 'https://www.sqlite.org/quickstart.html'),
    ('MongoDB|NoSQL', 'MongoDB getting started', 'https://www.mongodb.com/docs/manual/tutorial/getting-started/'),
    ('Redis|Caching (Redis)', 'Redis getting started', 'https://redis.io/docs/latest/develop/get-started/'),
    ('Elasticsearch|ELK Stack', 'Elastic getting started', 'https://www.elastic.co/docs/get-started'),
    ('Docker', 'Docker getting started', 'https://docs.docker.com/get-started/'),
    ('Kubernetes', 'Learn Kubernetes basics', 'https://kubernetes.io/docs/tutorials/kubernetes-basics/'),
    ('Kubernetes Networking', 'Kubernetes services and networking', 'https://kubernetes.io/docs/concepts/services-networking/'),
    ('Helm', 'Helm quick start', 'https://helm.sh/docs/intro/quickstart/'),
    ('AWS', 'AWS getting-started tutorials', 'https://aws.amazon.com/getting-started/hands-on/'),
    ('AWS S3', 'Amazon S3 getting started', 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/GetStartedWithS3.html'),
    ('AWS Networking', 'Amazon VPC getting started', 'https://docs.aws.amazon.com/vpc/latest/userguide/vpc-getting-started.html'),
    ('Cost Optimization', 'AWS cost optimization guidance', 'https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html'),
    ('Azure', 'Get started with Azure', 'https://learn.microsoft.com/en-us/azure/?product=popular'),
    ('GCP', 'Google Cloud getting started', 'https://cloud.google.com/docs/get-started'),
    ('Terraform', 'Terraform tutorials', 'https://developer.hashicorp.com/terraform/tutorials'),
    ('Ansible', 'Ansible getting started', 'https://docs.ansible.com/projects/ansible/latest/getting_started/index.html'),
    ('Git|GitHub', 'Pro Git book', 'https://git-scm.com/book/en/v2'),
    ('Git & DVC', 'DVC getting started', 'https://dvc.org/doc/start'),
    ('GitHub Actions|CI/CD', 'GitHub Actions quick start', 'https://docs.github.com/en/actions/get-started/quickstart'),
    ('GitLab', 'GitLab CI/CD quick start', 'https://docs.gitlab.com/ci/quick_start/'),
    ('Jenkins', 'Jenkins tutorials', 'https://www.jenkins.io/doc/tutorials/'),
    ('ArgoCD', 'Argo CD getting started', 'https://argo-cd.readthedocs.io/en/stable/getting_started/'),
    ('Prometheus', 'Prometheus getting started', 'https://prometheus.io/docs/prometheus/latest/getting_started/'),
    ('Grafana', 'Grafana fundamentals tutorial', 'https://grafana.com/tutorials/grafana-fundamentals/'),
    ('Grafana (SNMP)', 'Prometheus SNMP exporter guide', 'https://github.com/prometheus/snmp_exporter'),
    ('HashiCorp Vault', 'Vault foundations tutorials', 'https://developer.hashicorp.com/vault/tutorials/get-started'),
    ('Nginx', 'NGINX beginner guide', 'https://nginx.org/en/docs/beginners_guide.html'),
    ('HAProxy', 'HAProxy configuration tutorials', 'https://www.haproxy.com/documentation/haproxy-configuration-tutorials/'),
    ('RabbitMQ', 'RabbitMQ tutorials', 'https://www.rabbitmq.com/tutorials'),
    ('Networking|TCP/IP|OSI Model|Routing & Switching|VLANs & Subnetting', 'How networks and the Internet work', 'https://www.cloudflare.com/learning/network-layer/how-does-the-internet-work/'),
    ('BGP', 'How BGP works', 'https://www.cloudflare.com/learning/security/glossary/what-is-bgp/'),
    ('DNS', 'How DNS works', 'https://www.cloudflare.com/learning/dns/what-is-dns/'),
    ('Firewalls (iptables)', 'Netfilter and iptables documentation', 'https://www.netfilter.org/documentation/'),
    ('VPN (OpenVPN)', 'OpenVPN community resources', 'https://openvpn.net/community-resources/'),
    ('Container Security', 'Docker security guide', 'https://docs.docker.com/engine/security/'),
    ('Trivy (SAST/SCA)', 'Trivy getting started', 'https://www.trivy.dev/docs/latest/getting-started/installation/'),
    ('OWASP|OWASP Top 10', 'OWASP Top 10 learning guide', 'https://owasp.org/www-project-top-ten/'),
    ('Pen Testing|Penetration Testing|Web Security|Web App Security|Security Testing', 'OWASP Web Security Testing Guide', 'https://wstg.owasp.org/'),
    ('Threat Modeling|Security Architecture', 'OWASP threat modeling cheat sheet', 'https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html'),
    ('Cryptography', 'Cryptography engineering guidance', 'https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html'),
    ('Burp Suite', 'PortSwigger Web Security Academy', 'https://portswigger.net/web-security'),
    ('Wireshark', 'Wireshark user guide', 'https://www.wireshark.org/docs/wsug_html_chunked/'),
    ('Splunk|Splunk (SIEM)', 'Splunk search tutorial', 'https://help.splunk.com/en/splunk-enterprise/search/search-tutorial/9.4/introduction/about-the-search-tutorial'),
    ('Malware Analysis|Threat Intelligence|Red Teaming|Incident Response', 'MITRE ATT&CK learning resources', 'https://attack.mitre.org/resources/'),
    ('REST APIs', 'Microsoft web API design guide', 'https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design'),
    ('GraphQL', 'Learn GraphQL', 'https://graphql.org/learn/'),
    ('gRPC', 'gRPC introduction', 'https://grpc.io/docs/what-is-grpc/introduction/'),
    ('OAuth|JWT|Auth & JWT|Auth & Security', 'OWASP authentication guidance', 'https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html'),
    ('Design Patterns|SOLID|SOLID Principles|Microservices|Distributed Systems|System Design|Scalability|Domain-Driven Design|Event-Driven Arch|ADRs', 'Azure architecture patterns and guides', 'https://learn.microsoft.com/en-us/azure/architecture/'),
    ('MVVM Architecture', 'Android app architecture guide', 'https://developer.android.com/topic/architecture'),
    ('Playwright', 'Playwright getting started', 'https://playwright.dev/docs/intro'),
    ('Selenium', 'Selenium getting started', 'https://www.selenium.dev/documentation/webdriver/getting_started/'),
    ('Cypress', 'Cypress getting started', 'https://docs.cypress.io/app/get-started/why-cypress'),
    ('pytest', 'pytest getting started', 'https://docs.pytest.org/en/stable/getting-started.html'),
    ('JUnit|Testing (JUnit)', 'JUnit user guide', 'https://docs.junit.org/current/user-guide/'),
    ('Jest', 'Jest getting started', 'https://jestjs.io/docs/getting-started'),
    ('Vitest', 'Vitest getting started', 'https://vitest.dev/guide/'),
    ('k6|k6 (Performance)|Performance Testing', 'k6 getting started', 'https://grafana.com/docs/k6/latest/get-started/'),
    ('Postman|Postman & API Testing|API Testing', 'Postman learning center', 'https://learning.postman.com/docs/getting-started/overview/'),
    ('Agile|Scrum|Agile & SDLC', 'The Scrum Guide', 'https://scrumguides.org/scrum-guide.html'),
    ('Machine Learning|ML Fundamentals', 'Google machine learning crash course', 'https://developers.google.com/machine-learning/crash-course'),
    ('Scikit-learn|Classification Models|Regression Models|Clustering|Model Evaluation|Cross-Validation|Data Preprocessing', 'Scikit-learn user guide', 'https://scikit-learn.org/stable/user_guide.html'),
    ('Linear Algebra', 'MIT linear algebra course', 'https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/'),
    ('PyTorch|Neural Networks|Deep Learning', 'Learn PyTorch basics', 'https://docs.pytorch.org/tutorials/beginner/basics/intro.html'),
    ('TensorFlow', 'TensorFlow beginner tutorials', 'https://www.tensorflow.org/tutorials'),
    ('Pandas|NumPy & Pandas|Data Cleaning', 'Pandas getting-started tutorials', 'https://pandas.pydata.org/docs/getting_started/intro_tutorials/'),
    ('NumPy|NumPy & Pandas', 'NumPy absolute beginners guide', 'https://numpy.org/doc/stable/user/absolute_beginners.html'),
    ('Matplotlib', 'Matplotlib tutorials', 'https://matplotlib.org/stable/tutorials/index.html'),
    ('Statistics|Statistical Analysis|Descriptive Stats', 'NIST statistical methods handbook', 'https://www.itl.nist.gov/div898/handbook/'),
    ('Excel', 'Excel help and learning', 'https://support.microsoft.com/en-us/excel'),
    ('Tableau', 'Tableau getting-started tutorial', 'https://help.tableau.com/current/guides/get-started-tutorial/en-us/get-started-tutorial-home.htm'),
    ('Power BI', 'Power BI learning resources', 'https://learn.microsoft.com/en-us/power-bi/fundamentals/'),
    ('Spark', 'Apache Spark quick start', 'https://spark.apache.org/docs/latest/quick-start.html'),
    ('Airflow|Data Pipelines|ETL|ETL Concepts', 'Apache Airflow tutorials', 'https://airflow.apache.org/docs/apache-airflow/stable/tutorial/index.html'),
    ('Kafka', 'Apache Kafka quick start', 'https://kafka.apache.org/quickstart'),
    ('Hadoop', 'Apache Hadoop documentation', 'https://hadoop.apache.org/docs/stable/'),
    ('Snowflake', 'Snowflake tutorials', 'https://docs.snowflake.com/en/tutorials'),
    ('BigQuery', 'BigQuery quick starts', 'https://cloud.google.com/bigquery/docs/quickstarts'),
    ('dbt|Data Modeling|Data Quality', 'dbt quick starts', 'https://docs.getdbt.com/docs/get-started-dbt'),
    ('MLflow|MLOps Concepts', 'MLflow getting started', 'https://mlflow.org/docs/latest/ml/getting-started/'),
    ('NLP|LLM|LLM Concepts|Open-Source LLMs|Hugging Face|Transformers', 'Hugging Face LLM course', 'https://huggingface.co/learn/llm-course/chapter1/1'),
    ('Local LLMs (Ollama)', 'Ollama quick start', 'https://docs.ollama.com/quickstart'),
    ('Embeddings', 'Sentence Transformers quick start', 'https://www.sbert.net/docs/quickstart.html'),
    ('Vector Databases', 'Qdrant vector database quick start', 'https://qdrant.tech/documentation/quickstart/'),
    ('LangChain|RAG|RAG Pipelines', 'LangChain retrieval and RAG guide', 'https://docs.langchain.com/oss/python/langchain/retrieval'),
    ('AI Agents', 'Hugging Face agents course', 'https://huggingface.co/learn/agents-course/unit0/introduction'),
    ('Perl', 'Learn Perl', 'https://www.perl.org/learn.html'),
    ('MATLAB', 'MATLAB getting started', 'https://www.mathworks.com/help/matlab/getting-started-with-matlab.html'),
    ('Cassandra', 'Apache Cassandra getting started', 'https://cassandra.apache.org/doc/stable/cassandra/getting-started/index.html'),
    ('DynamoDB', 'Amazon DynamoDB getting started', 'https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStartedDynamoDB.html'),
    ('Windows Server', 'Windows Server learning resources', 'https://learn.microsoft.com/en-us/windows-server/'),
    ('Apache HTTP Server', 'Apache HTTP Server getting started', 'https://httpd.apache.org/docs/2.4/getting-started.html'),
    ('ActiveMQ|JMS', 'ActiveMQ getting started', 'https://activemq.apache.org/components/classic/documentation/getting-started'),
    ('JBoss', 'WildFly getting-started guides', 'https://www.wildfly.org/guides/'),
    ('Liquibase', 'Liquibase getting started', 'https://docs.liquibase.com/start/home.html'),
    ('CMake', 'CMake tutorial', 'https://cmake.org/cmake/help/latest/guide/tutorial/index.html'),
    ('vcpkg', 'vcpkg getting started', 'https://learn.microsoft.com/en-us/vcpkg/get_started/overview'),
    ('Maven', 'Maven in five minutes', 'https://maven.apache.org/guides/getting-started/maven-in-five-minutes.html'),
    ('Gradle', 'Gradle getting started', 'https://docs.gradle.org/current/userguide/getting_started.html'),
    ('XML', 'MDN XML introduction', 'https://developer.mozilla.org/en-US/docs/Web/XML/XML_introduction'),
    ('JSON', 'Working with JSON', 'https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting/JSON'),
    ('Jira', 'Jira getting started', 'https://www.atlassian.com/software/jira/guides/getting-started/introduction'),
    ('Confluence', 'Confluence getting started', 'https://www.atlassian.com/software/confluence/resources/guides/get-started/overview'),
    ('Salesforce', 'Salesforce platform development basics', 'https://trailhead.salesforce.com/content/learn/modules/platform-development-basics'),
    ('NetSuite', 'NetSuite learning and documentation', 'https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/index.html'),
    ('Zendesk', 'Zendesk developer tutorials and guides', 'https://developer.zendesk.com/documentation/'),
    ('Okta', 'Okta developer guides', 'https://developer.okta.com/docs/guides/'),
    ('SAP', 'SAP learning courses', 'https://learning.sap.com/'),
    ('ServiceNow', 'ServiceNow developer learning', 'https://developer.servicenow.com/dev.do#!/learn'),
)


def _resource(title: str, url: str, kind: str) -> dict:
    return {'title': title, 'url': url, 'kind': kind, 'source': urlsplit(url).hostname}


def _build_catalog() -> dict[str, list[dict]]:
    catalog: dict[str, list[dict]] = {}
    for names, slug, label in ROADMAP_GROUPS:
        resource = _resource(f'{label} learning path', f'https://roadmap.sh/{slug}', 'Learning path')
        for name in names.split('|'):
            catalog.setdefault(normalize_skill_name(name), []).append(resource)
    for names, title, url in GUIDE_GROUPS:
        resource = _resource(title, url, 'Official guide')
        for name in names.split('|'):
            catalog.setdefault(normalize_skill_name(name), []).append(resource)
    return catalog


RESOURCE_CATALOG = _build_catalog()


def learning_resources_for_skill(skill_name: str) -> list[dict]:
    """Return fresh, deduplicated resources; aliases use the same exact lookup."""

    resources = RESOURCE_CATALOG.get(normalize_skill_name(skill_name), [])
    if not resources:
        label = str(skill_name).strip()[:120]
        resources = [
            _resource('Search roadmap.sh for this skill', 'https://www.google.com/search?' + urlencode({'q': f'site:roadmap.sh {label}'}), 'Search'),
            _resource('Search for official guides and tutorials', 'https://www.google.com/search?' + urlencode({'q': f'{label} official documentation getting started tutorial'}), 'Search'),
        ]
    unique = {resource['url']: resource for resource in resources}
    return [dict(resource) for resource in list(unique.values())[:3]]


def with_learning_resources(skills: list[dict]) -> list[dict]:
    return [{**skill, 'learning_resources': learning_resources_for_skill(skill['skill_name'])} for skill in skills]

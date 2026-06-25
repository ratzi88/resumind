"""
ingest_roadmaps_v2.py — Smart roadmap.sh-backed skill ingestor.

Strategy:
  • Use roadmap.sh `topic` nodes (already 15-25 per role, well-ordered)
  • Apply a per-role SKILLS_MAP: generic label → concrete skill name (or None to skip)
  • Assign stage 1-4 from y-position quartiles (first 25% = Foundations, …)
  • Assign impact by stage (earlier = higher), then normalise to sum 100
  • Roles without JSON (devsecops, network-engineer) use hardcoded curated data

Run once:
    cd backend && python ingest_roadmaps_v2.py
"""
import os, json, math
import psycopg2, psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

ROADMAP_DIR = "/tmp/roadmapsh/src/data/roadmaps"

# Per-role override: original roadmap.sh topic label → concrete skill name
# None  → skip that topic entirely
# str   → rename to this concrete skill
SKILLS_MAP = {
    "devops": {
        "Learn a Programming Language": "Python",
        "Operating System":             "Linux",
        "Terminal Knowledge":           "Bash & Terminal",
        "Version Control Systems":      "Git",
        "VCS Hosting":                  None,
        "What is and how to setup X ?": None,
        "Containers":                   "Docker",
        "Cloud Providers":              "AWS",
        "Networking & Protocols":       "Networking",
        "Serverless":                   None,
        "Provisioning":                 "Terraform",
        "Configuration Management":     "Ansible",
        "CI / CD Tools":                "GitHub Actions",
        "Secret Management":            "HashiCorp Vault",
        "Infrastructure Monitoring":    "Prometheus",
        "Logs Management":              "ELK Stack",
        "Container Orchestration":      "Kubernetes",
        "Artifact Management":          None,
        "GitOps":                       "ArgoCD",
        "Service Mesh":                 None,
        "Cloud Design Patterns":        None,
        "Application Monitoring":       "Grafana",
    },
    "backend": {
        "Internet":                          "HTTP Basics",
        "Pick a Language":                   "Python",
        "Version Control Systems":           "Git",
        "Repo Hosting Services":             None,
        "Relational Databases":              "PostgreSQL",
        "Learn about APIs":                  "REST APIs",
        "Caching":                           "Redis",
        "Web Security":                      "Auth & Security",
        "Testing":                           "pytest",
        "CI / CD":                           "GitHub Actions",
        "More about Databases":              None,
        "Scaling Databases":                 None,
        "Architectural Patterns":            "Design Patterns",
        "Design and Development Principles": None,
        "Containerization vs Virtualization":"Docker",
        "Message Brokers":                   "RabbitMQ",
        "Search Engines":                    None,
        "Web Servers":                       "Nginx",
        "Real-Time Data":                    None,
        "NoSQL Databases":                   None,
        "Building For Scale":                "Scalability",
    },
    "frontend": {
        "Internet":               None,
        "HTML":                   "HTML",
        "CSS":                    "CSS",
        "JavaScript":             "JavaScript (ES6+)",
        "VCS Hosting":            None,
        "Version Control Systems":"Git",
        "Package Managers":       "npm",
        "Pick a Framework":       "React",
        "Writing CSS":            "Tailwind CSS",
        "CSS Architecture":       None,
        "CSS Preprocessors":      None,
        "Linters and Formatters": None,
        "Build Tools":            "Vite",
        "Module Bundlers":        None,
        "Web Security Basics":    "Web Security",
        "Testing":                "Vitest",
        "Authentication Strategies": None,
        "Web Components":         None,
        "Type Checkers":          "TypeScript",
        "SSR":                    "Next.js",
        "GraphQL":                None,
        "Static Site Generators": None,
        "PWAs":                   None,
        "Mobile Apps":            None,
        "Desktop Apps":           None,
    },
    "full-stack": {
        "HTML":         "HTML",
        "CSS":          "CSS",
        "JavaScript":   "JavaScript (ES6+)",
        "npm":          "npm",
        "Tailwind CSS": "Tailwind CSS",
        "React":        "React",
        "Git":          "Git",
        "GitHub":       None,
        "Node.js":      "Node.js",
        "PostgreSQL":   "PostgreSQL",
        "RESTful APIs": "REST APIs",
        "JWT Auth":     "Auth & JWT",
        "Redis":        "Redis",
        "Linux Basics": "Linux CLI",
        "Basic AWS Services": "AWS",
        "Monit":        None,
        "GitHub Actions": "GitHub Actions",
        "Ansible":      None,
        "Terraform":    None,
    },
    "machine-learning": {
        "Introduction":               None,
        "Linear Algebra":             "Linear Algebra",
        "Calculus":                   None,
        "Discrete Mathematics":       None,
        "Python":                     "Python",
        "Statistics":                 "Statistics",
        "Basic Syntax":               None,
        "Object Oriented Programming":None,
        "Essential libraries":        "NumPy & Pandas",
        "Data Sources":               None,
        "Data Formats":               None,
        "Preprocessing Techniques":   "Data Preprocessing",
        "What is Machine Learning?":  None,
        "Types of Machine Learning":  None,
        "Scikit-learn":               "Scikit-learn",
        "What is Supervised Learning?":None,
        "Classification":             "Classification Models",
        "Regression":                 "Regression Models",
        "What is Unsupervised Learning?": None,
        "Clustering":                 "Clustering",
        "Dimensionality Reduction":   None,
        "What is Reinforcement Learning?": None,
        "What is Model Evaluation?":  None,
        "Why is it important?":       None,
        "Metrics to Evaluate":        "Model Evaluation",
        "Validation Techniques":      "Cross-Validation",
        "Neural Network (NN) Basics": "Neural Networks",
        "Deep Learning Architectures":"Deep Learning",
        "Deep Learning Libraries":    "PyTorch",
        "Convolutional Neural Network": None,
        "Applications of CNNs":       None,
        "Recurrent Neural Networks":  None,
        "Attention Mechanisms":       "Transformers",
        "Autoencoders":               None,
        "Generative Adversarial Networks": None,
        "Natural Language Processing":"NLP",
        "Explainable AI":             None,
    },
    # cyber-security: only 6 generic topics in JSON → use HARDCODED below
    "ai-engineer": {
        "Introduction":            None,
        "Pre-trained Models":      "LLM Concepts",
        "OpenAI API":              "OpenAI API",
        "AI Safety and Ethics":    None,
        "OpenSource AI":           "Open-Source LLMs",
        "Hugging Face":            "Hugging Face",
        "Ollama":                  "Local LLMs (Ollama)",
        "What are Embeddings":     "Embeddings",
        "Open AI Embeddings API":  None,
        "Open-Source Embeddings":  None,
        "Vector Databases":        "Vector Databases",
        "RAG & Implementation":    "RAG Pipelines",
        "Open AI Assistant API":   None,
        "AI Agents":               "AI Agents",
        "Multimodal AI":           None,
        "Development Tools":       "LangChain",
    },
    "data-analyst": {
        "Introduction":                  None,
        "Types of Data Analytics":       "Analytics Concepts",
        "Analysis / Reporting with Excel":"Excel",
        "Learn a Programming Lang.":     "Python",
        "Data Manipulation Libraries":   "Pandas",
        "Data Visualisation Libraries":  "Matplotlib",
        "Data Collection":               "SQL",
        "Data Cleanup":                  "Data Cleaning",
        "Descriptive Analysis":          "Descriptive Stats",
        "Data Visualisation":            "Tableau",
        "Statistical Analysis":          "Statistical Analysis",
        "Machine Learning":              None,
        "Big Data Technologies":         "BigQuery",
        "Deep Learning (Optional)":      None,
    },
    "qa": {
        "Learn the Fundamentals":       "Testing Fundamentals",
        "SDLC Delivery Model":          "Agile & SDLC",
        "Manual Testing":               "Manual Testing",
        "Frontend Automation":          "Playwright",
        "Backend Automation":           "Postman & API Testing",
        "Accessibility Tests":          None,
        "Mobile Automation":            None,
        "Load & Performance Testing":   "k6 (Performance)",
        "Security Testing":             "Security Testing",
        "Email Testing":                None,
        "Reporting":                    None,
        "Monitoring & Logs":            None,
        "Version Control System":       "Git",
        "Repo Hosting Services":        None,
        "Repo Hosting Services":        None,
        "CI / CD":                      "GitHub Actions",
        "Headless Testing":             None,
    },
    "android": {
        "Pick a Language":     "Kotlin",
        "The Fundamentals":    "Android Fundamentals",
        "Version Control":     "Git",
        "App Components":      "Activities & Fragments",
        "Interface & Navigation": "Jetpack Compose",
        "Design & Architecture":  "MVVM Architecture",
        "Storage":             "Room Database",
        "Network":             "Retrofit (HTTP)",
        "Asynchronism":        "Coroutines & Flow",
        "Common Services":     "Firebase",
        "Linting":             None,
        "Testing":             "Testing (JUnit)",
        "Debugging":           None,
        "Distribution":        "Google Play",
    },
    "ios": {
        "Objective-C":                   None,
        "Pick a Language":               None,
        "Swift (Recommended)":           "Swift",
        "iOS Architecture":              None,
        "Core Programming Concepts":     "OOP Fundamentals",
        "Version Control":               "Git",
        "Xcode":                         "Xcode",
        "UIKit":                         None,
        "SwiftUI":                       "SwiftUI",
        "UI Design":                     None,
        "Core Animation":                None,
        "Architectural Patterns":        "MVVM Architecture",
        "Reactive Programming":          "Combine",
        "Delegate Pattern":              None,
        "Callbacks":                     None,
        "Data Persistence":              "Core Data",
        "Async / Await":                 "Async/Await",
        "JSON / XML":                    None,
        "Networking":                    "URLSession",
        "Concurrency and Multithreading":None,
        "Dependency Manager":            "Swift Package Manager",
        "Frameworks & Library":          None,
        "Accessibility":                 None,
        "Code Quality Tools":            None,
        "Debugging Techniques":          None,
        "CI / CD":                       "Fastlane",
        "App Store Distribution":        "App Store Connect",
        "TestFlight":                    None,
        "FastLane":                      None,
        "App Store Optimization (ASO)":  None,
        "Keeping Updated with WWDC":     None,
    },
    "mlops": {
        "Programming Fundamentals":        "Python",
        "Version Control Systems":         "Git & DVC",
        "Cloud Computing":                 "AWS",
        "Containerization":                "Docker",
        "Machine Learning Fundamentals":   "ML Fundamentals",
        "Data Engineering Fundamentals":   "Data Pipelines",
        "MLOps Principles":                "MLOps Concepts",
        "MLOps Components":                "MLflow",
        "Infrastructure as Code":          "Terraform",
    },
    # data-engineer: 43 topics (too many) → use HARDCODED below
    # software-architect: all generic topic labels → use HARDCODED below
}

# Roles with no JSON or whose topic list is too generic — fully hardcoded
HARDCODED = {
    "devsecops": [
        (1, "Linux CLI",           10), (1, "Networking",          8),
        (1, "Python",               7), (1, "Git",                  5),
        (2, "Docker",              10), (2, "Kubernetes",            8),
        (2, "GitHub Actions",       8), (2, "OWASP Top 10",          9),
        (3, "Trivy (SAST/SCA)",    8), (3, "HashiCorp Vault",       7),
        (3, "Terraform",            7), (3, "Container Security",    7),
        (4, "Threat Modeling",      7), (4, "Pen Testing",           7),
        (4, "SOC2 Compliance",      6), (4, "Splunk (SIEM)",         6),
    ],
    "network-engineer": [
        (1, "TCP/IP",               10), (1, "OSI Model",             8),
        (1, "Linux CLI",             7), (1, "Routing & Switching",   9),
        (2, "VLANs & Subnetting",   8), (2, "Firewalls (iptables)",  8),
        (2, "VPN (OpenVPN)",         7), (2, "Python Automation",     6),
        (3, "BGP",                   8), (3, "SDN (OpenFlow)",        7),
        (3, "Network Security",      8), (3, "HAProxy",               6),
        (4, "AWS Networking",        8), (4, "Kubernetes Networking",  6),
        (4, "Ansible",               7), (4, "Grafana (SNMP)",        4),
    ],
    "software-architect": [
        (1, "Design Patterns",      10), (1, "SOLID Principles",      9),
        (1, "Git",                   4), (1, "UML",                    4),
        (2, "REST APIs",             8), (2, "Microservices",          9),
        (2, "Docker",                7), (2, "PostgreSQL",             6),
        (3, "System Design",        10), (3, "Event-Driven Arch",      8),
        (3, "Domain-Driven Design",  8), (3, "Caching (Redis)",        6),
        (4, "Distributed Systems",   9), (4, "Scalability",            8),
        (4, "Security Architecture", 7), (4, "ADRs",                   3),
    ],
    "data-engineer": [
        (1, "Python",               10), (1, "SQL",                   10),
        (1, "Git",                   5), (1, "Linux CLI",               4),
        (2, "PostgreSQL",            8), (2, "ETL Concepts",            8),
        (2, "Pandas",                8), (2, "Data Modeling",           7),
        (3, "Apache Spark",          9), (3, "Apache Airflow",          8),
        (3, "Snowflake",             7), (3, "AWS S3",                  6),
        (4, "Apache Kafka",          8), (4, "dbt",                     7),
        (4, "Data Quality",          5), (4, "Cost Optimization",       4),
    ],
    "cyber-security": [
        (1, "Networking",            9), (1, "Linux",                   9),
        (1, "Python",                7), (1, "Git",                     3),
        (2, "OWASP Top 10",          9), (2, "Cryptography",            7),
        (2, "Wireshark",             7), (2, "Burp Suite",              8),
        (3, "Pen Testing",           9), (3, "Web App Security",        8),
        (3, "Splunk (SIEM)",         7), (3, "Incident Response",       7),
        (4, "Malware Analysis",      7), (4, "Threat Intelligence",     6),
        (4, "ISO 27001",             5), (4, "Red Teaming",             7),
    ],
}


def load_topics(role: str):
    """Return (label, y) pairs for all topic nodes, sorted by y."""
    path = os.path.join(ROADMAP_DIR, role, f"{role}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        nodes = json.load(f).get("nodes", [])
    topics = [(n["data"]["label"], n.get("position", {}).get("y", 0))
              for n in nodes if n.get("type") == "topic"]
    return sorted(topics, key=lambda x: x[1])


def assign_stages(skills_with_y):
    """Given [(name, y), …] assign stage 1-4 by quartile of y range."""
    if not skills_with_y:
        return []
    ys = [y for _, y in skills_with_y]
    lo, hi = min(ys), max(ys)
    span = hi - lo or 1
    def stage(y):
        q = (y - lo) / span
        if q < 0.25: return 1
        if q < 0.50: return 2
        if q < 0.75: return 3
        return 4
    return [(name, stage(y)) for name, y in skills_with_y]


def normalize_impacts(records):
    """records = [(stage, name, weight), …] → [(stage, name, impact)] summing to 100."""
    total = sum(w for _, _, w in records)
    if not total:
        return records
    return [(st, name, max(1, round(w / total * 100))) for st, name, w in records]


def build_from_json(role: str):
    if role not in SKILLS_MAP:
        return None          # fall through to HARDCODED
    override = SKILLS_MAP[role]
    topics = load_topics(role)
    if topics is None:
        return None

    # Apply override map, skip Nones, deduplicate renamed skills
    filtered = []
    seen = set()
    for label, y in topics:
        if label in override:
            new_name = override[label]
            if new_name is None:
                continue
        else:
            new_name = label        # keep original if not in map
        if new_name in seen:
            continue
        seen.add(new_name)
        filtered.append((new_name, y))

    if not filtered:
        return None

    staged = assign_stages(filtered)   # [(name, stage), …]

    # Impact weight: earlier stages score higher
    stage_weight = {1: 10, 2: 8, 3: 6, 4: 4}
    records = [(stage, name, stage_weight[stage]) for name, stage in staged]
    return normalize_impacts(records)


def build_hardcoded(role: str):
    """[(stage, name, weight), …] from HARDCODED, normalized."""
    raw = HARDCODED.get(role)
    if raw is None:
        return None
    return normalize_impacts(raw)


def ingest():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur  = conn.cursor()

    cur.execute("ALTER TABLE role_skills ADD COLUMN IF NOT EXISTS stage INT DEFAULT 1")
    conn.commit()
    print("stage column: ready")

    cur.execute("DELETE FROM role_skills")
    conn.commit()
    print("cleared old role_skills\n")

    ROLES = [
        "backend", "frontend", "full-stack", "devops", "devsecops",
        "data-engineer", "machine-learning", "cyber-security", "ai-engineer",
        "data-analyst", "qa", "software-architect", "mlops",
        "network-engineer", "android", "ios",
    ]

    total = 0
    for role in ROLES:
        records = build_from_json(role) or build_hardcoded(role)
        if not records:
            print(f"  {role}: SKIP (no data)")
            continue

        rows = [(role, name, f"Stage {st}", impact, st)
                for st, name, impact in records]

        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO role_skills (role, skill_name, category, impact, stage)
            VALUES %s
            ON CONFLICT (role, skill_name) DO UPDATE
              SET category = EXCLUDED.category,
                  impact   = EXCLUDED.impact,
                  stage    = EXCLUDED.stage
            """,
            rows,
        )
        conn.commit()
        by_stage = {}
        for st, name, _ in records:
            by_stage.setdefault(st, []).append(name)
        summary = "  |  ".join(
            f"S{s}: {', '.join(skills)}" for s, skills in sorted(by_stage.items())
        )
        print(f"  {role} ({len(rows)} skills)\n    {summary}\n")
        total += len(rows)

    cur.close()
    conn.close()
    print(f"Done — {total} skills across {len(ROLES)} roles.")


if __name__ == "__main__":
    ingest()

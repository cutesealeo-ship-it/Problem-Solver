import json
import os
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

client = Anthropic()
STORAGE_FILE = "problems.json"

# ============= Prompts =============
ANALYSIS_SYSTEM = """You are an expert problem analyzer. When given a problem, provide a clear analysis that includes:
1. Problem Summary: What is the core issue?
2. Key Factors: What are the important aspects to consider?
3. Potential Challenges: What obstacles might arise?

Be professional and thorough."""

SOLUTIONS_SYSTEM = """You are an expert problem solver. Generate 3-5 different solution approaches.
For each solution, provide: title, description, is_ideal (true for one best solution, false for others).
Return ONLY a valid JSON array with no markdown or extra text.
Example: [{"title": "Solution 1", "description": "...", "is_ideal": true}, ...]"""

STEPS_SYSTEM = """You are an expert at creating step-by-step instructions. Break down solutions into clear, actionable steps."""


# ============= API Functions =============
def ask_ai(user_message: str, system_prompt: str = None) -> str:
    """Send a message to Claude and get a response."""
    default_system = "You are a helpful problem solver. Provide clear, detailed, and practical solutions."

    message = client.messages.create(
        model="claude-haiku",
        max_tokens=1024,
        system=system_prompt or default_system,
        messages=[{"role": "user", "content": user_message}]
    )

    return message.content[0].text


# ============= Storage Functions =============
def load_problems():
    """Load problems from JSON file."""
    if not os.path.exists(STORAGE_FILE):
        return {"problems": []}
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)


def save_problems(data):
    """Save problems to JSON file."""
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_problem(problem_statement, analysis, solutions):
    """Add a new problem and solutions to storage."""
    data = load_problems()
    problem_id = f"problem_{len(data['problems']) + 1}_{datetime.now().strftime('%s')}"

    problem = {
        "id": problem_id,
        "timestamp": datetime.now().isoformat(),
        "problem_statement": problem_statement,
        "analysis": analysis,
        "solutions": solutions
    }

    data["problems"].append(problem)
    save_problems(data)
    return problem_id


# ============= Main App =============
def main():
    st.set_page_config(page_title="Problem Solver", layout="wide")

    # Initialize session state
    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "solutions" not in st.session_state:
        st.session_state.solutions = None
    if "problem_input" not in st.session_state:
        st.session_state.problem_input = ""
    if "expanded_solution" not in st.session_state:
        st.session_state.expanded_solution = None

    st.title("🤔 Problem Solver")
    st.write("Write down your problem and get AI-powered solutions with step-by-step guidance.")

    tab1, tab2 = st.tabs(["Solve Problem", "History"])

    with tab1:
        st.subheader("Enter Your Problem")
        problem_input = st.text_area(
            "What problem do you need help with?",
            placeholder="e.g., How do I solve quadratic equations? Or: How can I organize my study schedule?",
            height=100
        )

        if st.button("🚀 Analyze & Solve", type="primary"):
            if not problem_input.strip():
                st.error("Please enter a problem first!")
            else:
                with st.spinner("🤖 Analyzing your problem..."):
                    # Step 1: Analyze the problem
                    analysis = ask_ai(
                        f"Problem: {problem_input}",
                        ANALYSIS_SYSTEM
                    )

                with st.spinner("💡 Generating solutions..."):
                    # Step 2: Generate multiple solutions
                    solutions_prompt = f"Problem: {problem_input}\n\nAnalysis: {analysis}\n\nGenerate 3-5 different solution approaches."
                    solutions_json_str = ask_ai(solutions_prompt, SOLUTIONS_SYSTEM)

                    # Parse solutions - handle markdown code blocks
                    try:
                        # Remove markdown code blocks if present
                        cleaned = solutions_json_str.strip()
                        if cleaned.startswith("```"):
                            cleaned = cleaned.split("```")[1]
                            if cleaned.startswith("json"):
                                cleaned = cleaned[4:]
                        cleaned = cleaned.strip()
                        solutions = json.loads(cleaned)
                    except json.JSONDecodeError:
                        st.error("Error parsing solutions. Please try again.")
                        return

                # Step 3: Save to session state and storage
                st.session_state.problem_input = problem_input
                st.session_state.analysis = analysis
                st.session_state.solutions = solutions
                add_problem(problem_input, analysis, solutions)
                st.success("✅ Problem analyzed!")

        # Display results if they exist in session state
        if st.session_state.analysis and st.session_state.solutions:
            st.subheader("📋 Problem Analysis")
            st.write(st.session_state.analysis)

            st.subheader("💡 Possible Solutions")
            st.write(f"Found **{len(st.session_state.solutions)}** different approaches:")

            # Separate ideal solution from others
            all_sols = st.session_state.solutions
            ideal_solution = next((s for i, s in enumerate(all_sols) if s.get("is_ideal")) , None)
            ideal_idx = next((i for i, s in enumerate(all_sols) if s.get("is_ideal")), -1)
            other_solutions = [(i, s) for i, s in enumerate(all_sols) if not s.get("is_ideal")]

            # Display ideal solution first
            if ideal_solution is not None:
                st.markdown("### ⭐ Recommended Solution")
                if st.button(ideal_solution.get('title', 'Ideal Solution'), key=f"btn_ideal"):
                    st.session_state.expanded_solution = ideal_idx

                if st.session_state.expanded_solution == ideal_idx:
                    st.write(ideal_solution.get('description', ''))
                    if st.button(f"📝 Show Steps", key="steps_ideal"):
                        with st.spinner("📖 Generating step-by-step instructions..."):
                            steps_prompt = f"Solution Title: {ideal_solution.get('title')}\n\nSolution Description: {ideal_solution.get('description')}\n\nCreate detailed step-by-step instructions."
                            steps = ask_ai(steps_prompt, STEPS_SYSTEM)
                            st.write(steps)

            # Display other solutions
            if other_solutions:
                st.markdown("### 💡 Alternative Solutions")
                for num, (idx, solution) in enumerate(other_solutions, 1):
                    if st.button(f"{num}. {solution.get('title', 'Solution ' + str(num))}", key=f"btn_{idx}"):
                        st.session_state.expanded_solution = idx

                    if st.session_state.expanded_solution == idx:
                        st.write(solution.get('description', ''))
                        if st.button(f"📝 Show Steps", key=f"steps_{idx}"):
                            with st.spinner("📖 Generating step-by-step instructions..."):
                                steps_prompt = f"Solution Title: {solution.get('title')}\n\nSolution Description: {solution.get('description')}\n\nCreate detailed step-by-step instructions."
                                steps = ask_ai(steps_prompt, STEPS_SYSTEM)
                                st.write(steps)

    with tab2:
        st.subheader("📚 Problem History")
        problems = load_problems().get("problems", [])

        if not problems:
            st.info("No problems solved yet. Start by solving a problem in the 'Solve Problem' tab!")
        else:
            for problem in reversed(problems):
                with st.expander(f"📌 {problem['problem_statement'][:60]}... ({problem['timestamp'][:10]})"):
                    st.write(f"**Problem:** {problem['problem_statement']}")
                    st.write(f"**Analysis:**\n{problem['analysis']}")
                    st.write(f"**Number of Solutions:** {len(problem.get('solutions', []))}")

                    for i, sol in enumerate(problem.get("solutions", []), 1):
                        is_ideal = sol.get("is_ideal", False)
                        badge = "⭐" if is_ideal else f"•"
                        st.write(f"{badge} {sol.get('title', 'Solution')}")


if __name__ == "__main__":
    main()

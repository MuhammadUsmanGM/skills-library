#!/usr/bin/env python3
"""
Token Efficiency Demo - Prove MCP Code Execution savings

This script demonstrates the token efficiency of the MCP Code Execution pattern
compared to direct MCP tool loading.

Usage: python token_efficiency_demo.py
"""

import sys
import os
import argparse
from pathlib import Path


def count_tokens(text: str) -> int:
    """
    Estimate token count from text.
    Rough approximation: 1 token ≈ 4 characters
    """
    return len(text) // 4


def measure_skill_tokens(skill_dir: Path) -> dict:
    """Measure tokens loaded when using a skill."""
    result = {
        "skill_md": 0,
        "reference_md": 0,
        "scripts": 0,
        "total": 0
    }
    
    # SKILL.md - always loaded
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text()
        result["skill_md"] = count_tokens(content)
    
    # REFERENCE.md - loaded on-demand (not counted in base)
    reference_md = skill_dir / "REFERENCE.md"
    if reference_md.exists():
        content = reference_md.read_text()
        result["reference_md"] = count_tokens(content)
    
    # Scripts - NEVER loaded (0 tokens)
    scripts_dir = skill_dir / "scripts"
    if scripts_dir.exists():
        # Scripts are executed, not loaded into context
        # So they contribute 0 tokens
        result["scripts"] = 0
    
    # Total for skill-based approach
    result["total"] = result["skill_md"]
    
    return result


def estimate_direct_mcp_tokens(num_servers: int = 5) -> int:
    """
    Estimate tokens consumed by direct MCP tool loading.
    
    Based on Anthropic's measurements:
    - 1 MCP server with 5 tools ≈ 10,000 tokens
    - Scales linearly with number of servers
    """
    tokens_per_server = 10000
    return num_servers * tokens_per_server


def print_comparison(skill_name: str, skill_dir: Path):
    """Print token comparison."""
    print("=" * 70)
    print(f"Token Efficiency Analysis: {skill_name}")
    print("=" * 70)
    
    # Measure skill tokens
    skill_tokens = measure_skill_tokens(skill_dir)
    
    # Estimate direct MCP tokens (assuming 5 servers)
    direct_mcp_tokens = estimate_direct_mcp_tokens(5)
    
    print("\n📊 Token Breakdown")
    print("-" * 70)
    print(f"SKILL.md (loaded when triggered):     {skill_tokens['skill_md']:>8,} tokens")
    print(f"REFERENCE.md (on-demand, not counted): {skill_tokens['reference_md']:>8,} tokens")
    print(f"Scripts (executed, never loaded):          {skill_tokens['scripts']:>8,} tokens")
    print(f"                                         ─────────────")
    print(f"Total (Skill-based):                     {skill_tokens['total']:>8,} tokens")
    print()
    print(f"Direct MCP (5 servers loaded):          {direct_mcp_tokens:>8,} tokens")
    
    # Calculate savings
    savings = direct_mcp_tokens - skill_tokens['total']
    savings_pct = (savings / direct_mcp_tokens) * 100 if direct_mcp_tokens > 0 else 0
    
    print("\n💰 Token Savings")
    print("-" * 70)
    print(f"Tokens saved:                          {savings:>8,} tokens")
    print(f"Savings percentage:                       {savings_pct:>5.1f}%")
    print()
    
    # Context window impact
    context_window = 200000  # Claude's context window
    
    print("📈 Context Window Usage")
    print("-" * 70)
    print(f"Direct MCP:  {direct_mcp_tokens / context_window * 100:>5.1f}% of context window used BEFORE conversation")
    print(f"Skill-based: {skill_tokens['total'] / context_window * 100:>5.1f}% of context window used")
    print()
    
    # Practical impact
    print("💡 Practical Impact")
    print("-" * 70)
    print(f"With Direct MCP:")
    print(f"  - {direct_mcp_tokens:,} tokens consumed at startup")
    print(f"  - Only {context_window - direct_mcp_tokens:,} tokens available for conversation")
    print(f"  - ~{direct_mcp_tokens // 1000} pages of context lost")
    print()
    print(f"With MCP Code Execution:")
    print(f"  - {skill_tokens['total']:,} tokens consumed")
    print(f"  - {context_window - skill_tokens['total']:,} tokens available for conversation")
    print(f"  - Full context available for actual work")
    
    print("\n" + "=" * 70)
    
    return True


def demo_all_skills(skills_dir: Path):
    """Demonstrate token efficiency for all skills."""
    print("\n" + "=" * 70)
    print("SKILLS LIBRARY TOKEN EFFICIENCY SUMMARY")
    print("=" * 70)
    print()
    
    total_skill_tokens = 0
    skills_analyzed = 0
    
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
            skill_tokens = measure_skill_tokens(skill_dir)
            total_skill_tokens += skill_tokens['total']
            skills_analyzed += 1
            print(f"✓ {skill_dir.name}: {skill_tokens['total']:,} tokens")
    
    print()
    print(f"Total skills: {skills_analyzed}")
    print(f"Total tokens (all skills): {total_skill_tokens:,}")
    print(f"Average per skill: {total_skill_tokens // skills_analyzed:,}")
    print()
    
    # Compare to direct MCP
    direct_mcp_tokens = estimate_direct_mcp_tokens(5)
    savings = direct_mcp_tokens - total_skill_tokens
    savings_pct = (savings / direct_mcp_tokens) * 100 if direct_mcp_tokens > 0 else 0
    
    print(f"Direct MCP (5 servers): {direct_mcp_tokens:,} tokens")
    print(f"Skills Library: {total_skill_tokens:,} tokens")
    print(f"Savings: {savings:,} tokens ({savings_pct:.1f}%)")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Demonstrate token efficiency of MCP Code Execution"
    )
    parser.add_argument(
        "--skill",
        help="Analyze specific skill"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all skills"
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        help="Path to skills directory"
    )
    
    args = parser.parse_args()
    
    # Determine skills directory
    if args.skills_dir:
        skills_dir = Path(args.skills_dir)
    else:
        # Default to skills-library/.claude/skills
        script_dir = Path(__file__).parent
        skills_dir = script_dir.parent.parent / ".claude" / "skills"
    
    if not skills_dir.exists():
        print(f"Error: Skills directory not found: {skills_dir}")
        sys.exit(1)
    
    if args.skill:
        skill_dir = skills_dir / args.skill
        if not skill_dir.exists():
            print(f"Error: Skill not found: {skill_dir}")
            sys.exit(1)
        print_comparison(args.skill, skill_dir)
    elif args.all:
        demo_all_skills(skills_dir)
    else:
        # Default: show demo for first skill found
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                print_comparison(skill_dir.name, skill_dir)
                break
        else:
            print("No skills found in directory")
            sys.exit(1)


if __name__ == "__main__":
    main()

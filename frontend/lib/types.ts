export interface Competitor {
  name: string;
  url?: string;
  pricing?: string;
  gaps?: string[];
}

export interface Evidence {
  source: string;
  finding: string;
  url: string;
}

export interface Idea {
  idea_id: number;
  niche: string;
  domain: string;
  target_user: string;
  problem_statement: string;
  solution_type: string;
  solution_approach: string;
  market_gap_summary: string;
  reasoning: string;
  solvability_score: number;
  mvp_complexity: string;
  required_apis?: string[];
  competitors?: Competitor[];
  evidence?: Evidence[];
}

export interface ResearchResult {
  topic: string;
  ideas: Idea[];
}

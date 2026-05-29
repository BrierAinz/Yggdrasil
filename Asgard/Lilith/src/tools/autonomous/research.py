"""
Research - Deep research and information synthesis for Lilith
Handles: Multi-source research, fact verification, source comparison, summary generation
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus, urlparse

logger = logging.getLogger(__name__)


@dataclass
class Source:
    """Represents a research source"""

    url: str
    title: str
    snippet: str
    credibility_score: float = 0.5
    content: str = ""
    key_points: List[str] = field(default_factory=list)
    accessed_at: str = ""


@dataclass
class ResearchResult:
    """Represents the result of a research operation"""

    query: str
    summary: str
    sources: List[Source]
    key_findings: List[str]
    confidence_score: float
    contradictions: List[Dict[str, Any]]
    gaps: List[str]


class Research:
    """
    Autonomous tool for deep research and information synthesis.

    Capabilities:
    - quick_search: Fast search with basic results
    - deep_research: Multi-source research with synthesis
    - fact_check: Verify specific claims against sources
    - compare_sources: Compare information across sources
    - summarize_topic: Generate comprehensive summary
    - find_expert_sources: Find authoritative sources on topic
    """

    def __init__(self):
        self.web_browser = None
        self.max_sources_deep = 5
        self.max_sources_quick = 3
        self.min_content_length = 100
        self.credible_domains = [
            ".edu",
            ".gov",
            ".ac.uk",
            ".ac.jp",  # Academic/Gov
            "github.com",
            "stackoverflow.com",
            "docs.",
            "documentation.",
            "wikipedia.org",
            "wikidata.org",
            "arxiv.org",
            "ieee.org",
            "acm.org",
            "nature.com",
            "science.org",
            "ncbi.nlm.nih.gov",
            "who.int",
            "un.org",
            "worldbank.org",
            "reuters.com",
            "ap.org",
            "bbc.com",
            "nytimes.com",
        ]
        self.low_credibility_patterns = [
            "rumor",
            "unconfirmed",
            "allegedly",
            "supposedly",
            "might be",
            "could be",
            "possibly",
            "reportedly",
            "rumores",
            "sin confirmar",
            "supuestamente",
            "presuntamente",
        ]

    def _get_browser(self):
        """Lazy initialization of WebBrowser"""
        if self.web_browser is None:
            from src.tools.autonomous.web_browser import WebBrowser

            self.web_browser = WebBrowser()
        return self.web_browser

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute research operation

        Args:
            action: The research operation to perform
            **kwargs: Operation-specific parameters

        Returns:
            Dict with operation results
        """
        try:
            if action == "quick_search":
                return await self._quick_search(
                    kwargs.get("query"),
                    kwargs.get("num_results", self.max_sources_quick),
                )
            elif action == "deep_research":
                return await self._deep_research(
                    kwargs.get("query"),
                    kwargs.get("num_sources", self.max_sources_deep),
                    kwargs.get("include_synthesis", True),
                )
            elif action == "fact_check":
                return await self._fact_check(
                    kwargs.get("claim"), kwargs.get("sources", [])
                )
            elif action == "compare_sources":
                return await self._compare_sources(
                    kwargs.get("query"), kwargs.get("urls", [])
                )
            elif action == "summarize_topic":
                return await self._summarize_topic(
                    kwargs.get("topic"), kwargs.get("context", "")
                )
            elif action == "find_expert_sources":
                return await self._find_expert_sources(
                    kwargs.get("topic"), kwargs.get("num_results", 5)
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown research action: {action}",
                    "action": action,
                }
        except Exception as e:
            logger.error(f"Research operation failed: {e}")
            return {"success": False, "error": str(e), "action": action}

    async def _quick_search(self, query: str, num_results: int = 3) -> Dict[str, Any]:
        """Quick search with basic results"""
        if not query:
            return {"success": False, "error": "Query is required"}

        browser = self._get_browser()

        try:
            # Use WebBrowser to search
            result = await browser.execute(
                "search", query=query, num_results=num_results
            )

            if not result.get("success"):
                return result

            search_results = result.get("results", [])

            # Format sources
            sources = []
            for item in search_results:
                source = Source(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                    credibility_score=self._calculate_credibility(item.get("url", "")),
                    accessed_at=datetime.now().isoformat(),
                )
                sources.append(source)

            # Sort by credibility
            sources.sort(key=lambda x: x.credibility_score, reverse=True)

            return {
                "success": True,
                "query": query,
                "sources": [
                    {
                        "url": s.url,
                        "title": s.title,
                        "snippet": s.snippet,
                        "credibility": s.credibility_score,
                    }
                    for s in sources
                ],
                "count": len(sources),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "query": query}

    async def _deep_research(
        self, query: str, num_sources: int = 5, include_synthesis: bool = True
    ) -> Dict[str, Any]:
        """Deep research with content extraction and synthesis"""
        if not query:
            return {"success": False, "error": "Query is required"}

        browser = self._get_browser()

        try:
            # Step 1: Search for sources
            search_result = await browser.execute(
                "search", query=query, num_results=num_sources * 2
            )

            if not search_result.get("success"):
                return search_result

            search_results = search_result.get("results", [])

            # Step 2: Extract content from top sources
            sources = []
            for item in search_results[:num_sources]:
                url = item.get("url", "")
                title = item.get("title", "")
                snippet = item.get("snippet", "")

                # Try to extract full content
                content = snippet
                key_points = []

                try:
                    visit_result = await browser.execute(
                        "visit", url=url, extract_text=True, extract_links=False
                    )
                    if visit_result.get("success"):
                        content = visit_result.get("text", snippet)[
                            :5000
                        ]  # Limit content
                        key_points = self._extract_key_points(content, query)
                except Exception as e:
                    logger.warning(f"Failed to extract content from {url}: {e}")

                source = Source(
                    url=url,
                    title=title,
                    snippet=snippet,
                    content=content,
                    key_points=key_points,
                    credibility_score=self._calculate_credibility(url),
                    accessed_at=datetime.now().isoformat(),
                )
                sources.append(source)

            # Step 3: Sort by credibility and content quality
            sources.sort(
                key=lambda x: (x.credibility_score, len(x.content)), reverse=True
            )

            # Step 4: Identify key findings
            all_key_points = []
            for source in sources:
                all_key_points.extend(source.key_points)

            # Remove duplicates while preserving order
            unique_findings = list(dict.fromkeys(all_key_points))

            # Step 5: Check for contradictions
            contradictions = self._find_contradictions(sources)

            # Step 6: Identify gaps
            gaps = self._identify_gaps(query, sources, unique_findings)

            # Step 7: Calculate overall confidence
            confidence = self._calculate_overall_confidence(sources, contradictions)

            # Step 8: Generate synthesis
            summary = ""
            if include_synthesis:
                summary = self._generate_synthesis(query, sources, unique_findings[:10])

            research_result = ResearchResult(
                query=query,
                summary=summary,
                sources=sources,
                key_findings=unique_findings[:15],
                confidence_score=confidence,
                contradictions=contradictions,
                gaps=gaps,
            )

            return {
                "success": True,
                "query": query,
                "summary": summary,
                "key_findings": research_result.key_findings,
                "confidence_score": round(confidence, 2),
                "sources": [
                    {
                        "url": s.url,
                        "title": s.title,
                        "credibility": round(s.credibility_score, 2),
                        "key_points": s.key_points[:5],
                    }
                    for s in sources
                ],
                "contradictions": contradictions,
                "gaps": gaps,
                "sources_analyzed": len(sources),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "query": query}

    async def _fact_check(
        self, claim: str, sources: List[str] = None
    ) -> Dict[str, Any]:
        """Verify a specific claim against sources"""
        if not claim:
            return {"success": False, "error": "Claim is required"}

        browser = self._get_browser()

        try:
            # Search for the claim
            search_query = f"fact check {claim}"
            search_result = await browser.execute(
                "search", query=search_query, num_results=5
            )

            if not search_result.get("success"):
                return search_result

            # Analyze sources for verification
            verification_results = []
            supporting = 0
            contradicting = 0
            neutral = 0

            for item in search_result.get("results", []):
                url = item.get("url", "")
                title = item.get("title", "")
                snippet = item.get("snippet", "").lower()

                # Check sentiment in snippet
                claim_lower = claim.lower()
                credibility = self._calculate_credibility(url)

                # Simple keyword matching for verification
                support_keywords = [
                    "true",
                    "correct",
                    "confirmed",
                    "verified",
                    "yes",
                    "sÃ­",
                    "verdadero",
                    "confirmado",
                ]
                contradict_keywords = [
                    "false",
                    "incorrect",
                    "debunked",
                    "misleading",
                    "no",
                    "falso",
                    "incorrecto",
                ]

                status = "neutral"
                if any(kw in snippet for kw in support_keywords):
                    status = "supporting"
                    supporting += 1
                elif any(kw in snippet for kw in contradict_keywords):
                    status = "contradicting"
                    contradicting += 1
                else:
                    neutral += 1

                verification_results.append(
                    {
                        "url": url,
                        "title": title,
                        "status": status,
                        "credibility": credibility,
                        "snippet": item.get("snippet", "")[:200],
                    }
                )

            # Calculate verification score
            total_weighted = supporting + contradicting
            if total_weighted > 0:
                verification_score = supporting / total_weighted
            else:
                verification_score = 0.5

            # Determine verdict
            if verification_score > 0.7:
                verdict = "likely_true"
            elif verification_score < 0.3:
                verdict = "likely_false"
            else:
                verdict = "uncertain"

            return {
                "success": True,
                "claim": claim,
                "verdict": verdict,
                "verification_score": round(verification_score, 2),
                "supporting_count": supporting,
                "contradicting_count": contradicting,
                "neutral_count": neutral,
                "sources": verification_results,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "claim": claim}

    async def _compare_sources(self, query: str, urls: List[str]) -> Dict[str, Any]:
        """Compare information across multiple sources"""
        if not urls or len(urls) < 2:
            return {
                "success": False,
                "error": "At least 2 URLs are required for comparison",
            }

        browser = self._get_browser()

        try:
            sources_data = []

            for url in urls:
                result = await browser.execute(
                    "visit", url=url, extract_text=True, extract_links=False
                )

                if result.get("success"):
                    content = result.get("text", "")[:3000]
                    key_points = self._extract_key_points(content, query)

                    sources_data.append(
                        {
                            "url": url,
                            "title": result.get("title", ""),
                            "content_preview": content[:500],
                            "key_points": key_points,
                            "credibility": self._calculate_credibility(url),
                        }
                    )
                else:
                    sources_data.append(
                        {
                            "url": url,
                            "title": "Failed to load",
                            "error": result.get("error", "Unknown error"),
                            "credibility": 0,
                        }
                    )

            # Find agreements and disagreements
            all_points = []
            for source in sources_data:
                all_points.extend(source.get("key_points", []))

            # Simple similarity check
            agreements = []
            unique_points = {}

            for point in all_points:
                normalized = point.lower().strip()
                if normalized in unique_points:
                    unique_points[normalized]["count"] += 1
                    unique_points[normalized]["sources"].append(point)
                else:
                    unique_points[normalized] = {"count": 1, "sources": [point]}

            # Points mentioned by multiple sources = agreements
            for normalized, data in unique_points.items():
                if data["count"] > 1:
                    agreements.append(
                        {"point": data["sources"][0], "source_count": data["count"]}
                    )

            # Unique points per source = potential disagreements
            unique_per_source = {s["url"]: [] for s in sources_data}
            for normalized, data in unique_points.items():
                if data["count"] == 1:
                    for source in sources_data:
                        if data["sources"][0] in source.get("key_points", []):
                            unique_per_source[source["url"]].append(data["sources"][0])

            return {
                "success": True,
                "query": query,
                "sources": sources_data,
                "agreements": agreements,
                "unique_points": unique_per_source,
                "agreement_count": len(agreements),
                "comparison_summary": f"Found {len(agreements)} points of agreement across sources",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _summarize_topic(self, topic: str, context: str = "") -> Dict[str, Any]:
        """Generate comprehensive summary of a topic"""
        # This uses deep_research as a foundation
        research_result = await self._deep_research(
            topic, num_sources=5, include_synthesis=True
        )

        if not research_result.get("success"):
            return research_result

        # Add context-specific information if provided
        if context:
            research_result["context"] = context
            research_result[
                "summary"
            ] = f"Summary of {topic} (with context: {context}):\n\n{research_result.get('summary', '')}"

        return research_result

    async def _find_expert_sources(
        self, topic: str, num_results: int = 5
    ) -> Dict[str, Any]:
        """Find authoritative sources on a topic"""
        browser = self._get_browser()

        try:
            # Search with academic/expert keywords
            expert_queries = [
                f"{topic} site:.edu OR site:.gov",
                f"{topic} research paper",
                f"{topic} expert opinion",
            ]

            all_results = []
            for query in expert_queries[:2]:  # Limit to avoid too many requests
                result = await browser.execute(
                    "search", query=query, num_results=num_results
                )
                if result.get("success"):
                    all_results.extend(result.get("results", []))

            # Filter and score for credibility
            expert_sources = []
            for item in all_results:
                url = item.get("url", "")
                credibility = self._calculate_credibility(url)

                if credibility >= 0.7:  # High credibility threshold
                    expert_sources.append(
                        {
                            "url": url,
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "credibility": credibility,
                            "type": self._classify_source_type(url),
                        }
                    )

            # Sort by credibility
            expert_sources.sort(key=lambda x: x["credibility"], reverse=True)

            return {
                "success": True,
                "topic": topic,
                "expert_sources": expert_sources[:num_results],
                "count": len(expert_sources[:num_results]),
            }

        except Exception as e:
            return {"success": False, "error": str(e), "topic": topic}

    def _calculate_credibility(self, url: str) -> float:
        """Calculate credibility score for a URL"""
        score = 0.5  # Base score

        domain = urlparse(url).netloc.lower()

        # Check credible domains
        for credible in self.credible_domains:
            if credible in domain:
                score += 0.3
                break

        # Penalize suspicious patterns
        suspicious = ["blog", "forum", "social", "reddit", "facebook", "twitter"]
        for susp in suspicious:
            if susp in domain:
                score -= 0.1

        # Bonus for HTTPS
        if url.startswith("https://"):
            score += 0.05

        return min(1.0, max(0.0, score))

    def _classify_source_type(self, url: str) -> str:
        """Classify the type of source"""
        domain = urlparse(url).netloc.lower()

        if ".edu" in domain or "university" in domain or "college" in domain:
            return "academic"
        elif ".gov" in domain:
            return "government"
        elif "github.com" in domain:
            return "code_repository"
        elif "stackoverflow" in domain or "stackexchange" in domain:
            return "q_a_forum"
        elif "wikipedia" in domain:
            return "encyclopedia"
        elif "news" in domain or any(
            n in domain for n in ["reuters", "ap.org", "bbc", "nytimes"]
        ):
            return "news"
        elif "docs." in domain or "documentation" in domain:
            return "documentation"
        else:
            return "general"

    def _extract_key_points(self, content: str, query: str) -> List[str]:
        """Extract key points from content relevant to query"""
        key_points = []

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", content)

        query_terms = set(query.lower().split())

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30 or len(sentence) > 300:
                continue

            # Check relevance to query
            sentence_lower = sentence.lower()
            relevance_score = sum(1 for term in query_terms if term in sentence_lower)

            if relevance_score > 0:
                # Check for key indicators
                indicators = [
                    "is",
                    "are",
                    "was",
                    "were",
                    "means",
                    "refers",
                    "defined",
                    "important",
                    "significant",
                    "key",
                    "main",
                    "primary",
                    "es",
                    "son",
                    "era",
                    "significa",
                    "importante",
                    "clave",
                ]

                if any(ind in sentence_lower for ind in indicators):
                    key_points.append(sentence)

        # Return top relevant points
        return key_points[:8]

    def _find_contradictions(self, sources: List[Source]) -> List[Dict[str, Any]]:
        """Find potential contradictions between sources"""
        contradictions = []

        # Simple contradiction detection based on negation patterns
        for i, source1 in enumerate(sources):
            for source2 in sources[i + 1 :]:
                for point1 in source1.key_points:
                    point1_lower = point1.lower()
                    for point2 in source2.key_points:
                        point2_lower = point2.lower()

                        # Check for direct negation patterns
                        if self._are_contradictory(point1_lower, point2_lower):
                            contradictions.append(
                                {
                                    "source1": source1.url,
                                    "source2": source2.url,
                                    "point1": point1[:200],
                                    "point2": point2[:200],
                                }
                            )

        return contradictions

    def _are_contradictory(self, text1: str, text2: str) -> bool:
        """Check if two texts are likely contradictory"""
        # Very simple heuristic: same subject, opposite verb
        negation_words = [
            "not",
            "no",
            "never",
            "without",
            "none",
            "no es",
            "nunca",
            "sin",
            "ninguno",
            "falso",
        ]

        # If one has negation and other doesn't, might be contradictory
        has_neg1 = any(neg in text1 for neg in negation_words)
        has_neg2 = any(neg in text2 for neg in negation_words)

        if has_neg1 != has_neg2:
            # Check for significant word overlap
            words1 = set(text1.split())
            words2 = set(text2.split())
            overlap = len(words1.intersection(words2))

            if overlap >= 3:  # Significant overlap suggests same topic
                return True

        return False

    def _identify_gaps(
        self, query: str, sources: List[Source], findings: List[str]
    ) -> List[str]:
        """Identify gaps in the research"""
        gaps = []

        # Check for common gap indicators
        query_terms = query.lower().split()

        # If few sources, might need more
        if len(sources) < 3:
            gaps.append("Limited number of sources available")

        # If low credibility sources
        high_cred_sources = [s for s in sources if s.credibility_score >= 0.7]
        if len(high_cred_sources) < 2:
            gaps.append("Few high-credibility sources found")

        # Check recency (simplified - would need date extraction)
        if len(findings) < 5:
            gaps.append("Limited information available on specific aspects")

        return gaps

    def _calculate_overall_confidence(
        self, sources: List[Source], contradictions: List[Dict]
    ) -> float:
        """Calculate overall confidence score"""
        if not sources:
            return 0.0

        # Average credibility
        avg_credibility = sum(s.credibility_score for s in sources) / len(sources)

        # Penalty for contradictions
        contradiction_penalty = min(0.3, len(contradictions) * 0.1)

        # Bonus for source diversity
        domains = set(urlparse(s.url).netloc for s in sources)
        diversity_bonus = min(0.1, len(domains) * 0.02)

        return min(1.0, avg_credibility + diversity_bonus - contradiction_penalty)

    def _generate_synthesis(
        self, query: str, sources: List[Source], key_findings: List[str]
    ) -> str:
        """Generate a synthesis of the research"""
        if not sources:
            return "No sources found for this query."

        # Get top sources by credibility
        top_sources = sorted(sources, key=lambda x: x.credibility_score, reverse=True)[
            :3
        ]

        synthesis_parts = []

        # Introduction
        synthesis_parts.append(
            f"Research on '{query}' found {len(sources)} sources with varying credibility levels."
        )

        # Key findings summary
        if key_findings:
            synthesis_parts.append(f"\nKey findings ({len(key_findings)} identified):")
            for i, finding in enumerate(key_findings[:5], 1):
                synthesis_parts.append(f"{i}. {finding}")

        # Source credibility
        high_cred = [s for s in sources if s.credibility_score >= 0.7]
        synthesis_parts.append(
            f"\nSource quality: {len(high_cred)} high-credibility sources identified."
        )

        # Recommendations
        if high_cred:
            synthesis_parts.append(
                f"Most reliable source: {high_cred[0].title} ({high_cred[0].url})"
            )

        return "\n".join(synthesis_parts)

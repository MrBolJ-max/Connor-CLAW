"""
SYN Systems — Content & SEO Agent
Organic Growth Engine

Creates compliant, high-ranking content with human oversight.
Builds topical authority while you focus on operations.
85%+ ranking improvement average.

Integrations: WordPress, Webflow, Shopify
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import httpx
from loguru import logger
from core.claude_client import claude
from core.config import settings


class ContentType(str, Enum):
    BLOG_POST = "blog_post"
    LINKEDIN = "linkedin"
    EMAIL_SEQUENCE = "email_sequence"
    AD_COPY = "ad_copy"
    CASE_STUDY = "case_study"
    SEO_ARTICLE = "seo_article"
    LANDING_PAGE = "landing_page"
    FAQ_PAGE = "faq_page"
    SOCIAL_CAPTION = "social_caption"


class Platform(str, Enum):
    WORDPRESS = "wordpress"
    WEBFLOW = "webflow"
    SHOPIFY = "shopify"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"


@dataclass
class ContentBrief:
    title: str
    content_type: ContentType
    primary_keyword: str
    secondary_keywords: list[str] = field(default_factory=list)
    target_audience: str = "Australian business owners"
    industry: str = ""
    word_count: int = 1200
    tone: str = "professional, authoritative, solution-focused"
    cta: str = "Book a free AI readiness audit"
    platform: Optional[Platform] = None
    client_id: Optional[str] = None


@dataclass
class GeneratedContent:
    brief: ContentBrief
    title: str
    meta_description: str
    body: str
    cta_section: str
    tags: list[str]
    estimated_word_count: int
    seo_score_estimate: int
    published_url: str = ""
    platform_post_id: str = ""


class ContentSEOAgent:
    """
    AI-powered content creation and SEO agent.
    Researches keywords, writes content, optimises for search,
    and publishes directly to WordPress/Webflow/Shopify.
    """

    SYSTEM_PROMPT = """You are SYN Systems' Content & SEO Agent — an expert content strategist
and SEO specialist focused on AI automation services for Australian businesses.

Your content always:
- Targets specific keywords naturally (density 1-2%)
- Uses clear headings (H2, H3) for structure
- Includes real statistics and social proof
- Speaks to pain points before solutions
- Has a compelling, specific CTA
- Follows E-E-A-T principles (Experience, Expertise, Authority, Trust)
- Is compliant and fact-checked

SYN Systems' core messages:
- Deploy AI agents in 48 hours
- 95%+ first-call resolution
- 40+ hours/week reclaimed
- 3x conversion improvement
- 85%+ SEO ranking improvement
- Trusted by companies in AU, US, UK"""

    INDUSTRIES = [
        "B2B Services", "Healthcare", "SaaS", "Technology", "Real Estate", "E-commerce"
    ]

    KEYWORD_CLUSTERS = {
        "AI automation": [
            "AI automation Australia",
            "business automation AI",
            "AI agent for business",
            "automate business processes Australia",
        ],
        "AI receptionist": [
            "AI phone answering service Australia",
            "AI receptionist small business",
            "24/7 virtual receptionist AI",
        ],
        "lead generation": [
            "AI lead generation Australia",
            "automated lead capture",
            "AI lead qualification",
        ],
        "AI for healthcare": [
            "AI receptionist medical practice",
            "healthcare automation Australia",
            "medical clinic AI tools",
        ],
        "AI for real estate": [
            "AI for real estate agents Australia",
            "property management automation",
            "real estate lead follow up AI",
        ],
    }

    def research_keywords(self, topic: str, industry: str = "") -> dict:
        """Generate keyword research using Claude."""
        result = claude.extract_json(
            system_prompt=(
                "You are an SEO keyword research specialist for Australian businesses. "
                "Provide realistic keyword data."
            ),
            user_message=(
                f"Research keywords for: '{topic}'\n"
                f"Industry: {industry or 'general business'}\n"
                f"Target market: Australian businesses\n\n"
                "Return JSON:\n"
                "{\n"
                '  "primary_keyword": "...",\n'
                '  "secondary_keywords": ["...", "..."],\n'
                '  "long_tail": ["...", "..."],\n'
                '  "search_intent": "informational|commercial|transactional",\n'
                '  "estimated_monthly_searches_au": <number>,\n'
                '  "competition": "low|medium|high",\n'
                '  "content_recommendation": "..."\n'
                "}"
            ),
            max_tokens=400,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"primary_keyword": topic, "secondary_keywords": [], "long_tail": []}

    def generate_content(self, brief: ContentBrief) -> GeneratedContent:
        """Generate full content piece from a brief."""
        logger.info(f"Generating {brief.content_type.value}: {brief.title}")

        type_instructions = {
            ContentType.BLOG_POST: (
                f"Write a {brief.word_count}-word blog post. "
                "Include: intro hook, 4-6 H2 sections, statistics, conclusion with CTA."
            ),
            ContentType.SEO_ARTICLE: (
                f"Write a {brief.word_count}-word SEO article. "
                "Optimise for primary keyword naturally. Include FAQ section at end."
            ),
            ContentType.LINKEDIN: (
                "Write a LinkedIn post (300-500 words). "
                "Hook in first line. Use line breaks for readability. End with question or CTA."
            ),
            ContentType.EMAIL_SEQUENCE: (
                "Write a 5-email nurture sequence. "
                "Email 1: Welcome/value. Email 2: Education. Email 3: Social proof. "
                "Email 4: Objection handling. Email 5: Offer/CTA."
            ),
            ContentType.AD_COPY: (
                "Write 3 ad variations (Facebook/Google). "
                "Each: Headline (30 chars), Description (90 chars), CTA. "
                "Test different angles: pain, benefit, social proof."
            ),
            ContentType.CASE_STUDY: (
                "Write a case study: Client background, Challenge, Solution (SYN Systems agents), "
                "Results with metrics, Client quote, CTA."
            ),
            ContentType.LANDING_PAGE: (
                "Write landing page copy: Hero headline + subheadline, 3 benefit blocks, "
                "social proof section, FAQ (5 questions), final CTA section."
            ),
            ContentType.FAQ_PAGE: (
                "Write 15 FAQs about AI automation for businesses. "
                "Cover: what it is, how it works, cost, timeline, industries, ROI."
            ),
            ContentType.SOCIAL_CAPTION: (
                "Write 5 social media captions (Instagram/Facebook). "
                "Each under 150 words. Include 5-8 relevant hashtags."
            ),
        }

        instruction = type_instructions.get(brief.content_type, f"Write content about {brief.title}.")

        full_content = claude.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=(
                f"{instruction}\n\n"
                f"Title/Topic: {brief.title}\n"
                f"Primary Keyword: {brief.primary_keyword}\n"
                f"Secondary Keywords: {', '.join(brief.secondary_keywords)}\n"
                f"Target Audience: {brief.target_audience}\n"
                f"Industry: {brief.industry or 'General'}\n"
                f"Tone: {brief.tone}\n"
                f"CTA: {brief.cta}"
            ),
            max_tokens=2500,
        )

        meta = claude.chat(
            system_prompt="Write SEO meta descriptions. Under 160 characters. Include primary keyword.",
            user_message=f"Write meta description for: {brief.title}\nKeyword: {brief.primary_keyword}",
            max_tokens=60,
            temperature=0.3,
        )

        tags = claude.chat(
            system_prompt="Generate 5-8 relevant tags/categories as JSON array. No explanation.",
            user_message=f"Tags for: {brief.title} | {brief.industry} | {brief.primary_keyword}",
            max_tokens=80,
            temperature=0.2,
        )
        try:
            tag_list = json.loads(tags)
        except json.JSONDecodeError:
            tag_list = [brief.primary_keyword, brief.industry, "AI automation"]

        word_count = len(full_content.split())
        seo_score = min(95, 60 + (word_count // 50) + (3 if brief.primary_keyword.lower() in full_content.lower() else 0))

        return GeneratedContent(
            brief=brief,
            title=brief.title,
            meta_description=meta.strip(),
            body=full_content,
            cta_section=f"Ready to automate your business? {brief.cta}",
            tags=tag_list if isinstance(tag_list, list) else [brief.primary_keyword],
            estimated_word_count=word_count,
            seo_score_estimate=seo_score,
        )

    def generate_content_calendar(self, industry: str, weeks: int = 4) -> list[dict]:
        """Generate a content calendar for a client."""
        result = claude.extract_json(
            system_prompt=(
                "You are a content strategist specialising in AI automation services. "
                "Create realistic, actionable content calendars."
            ),
            user_message=(
                f"Create a {weeks}-week content calendar for a business in: {industry}\n"
                f"Focus: AI automation, business efficiency, SYN Systems services.\n"
                f"Mix: blog posts, LinkedIn, emails, case studies.\n\n"
                f"Return JSON array of {weeks * 3} content items:\n"
                '[{"week": 1, "day": "Monday", "type": "blog_post", '
                '"title": "...", "primary_keyword": "...", "goal": "..."}]'
            ),
            max_tokens=1200,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    async def publish_to_wordpress(self, content: GeneratedContent) -> bool:
        """Publish content to WordPress via REST API."""
        if not all([settings.wordpress_url, settings.wordpress_username, settings.wordpress_app_password]):
            logger.warning("WordPress not configured — skipping publish")
            return False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.wordpress_url}/wp-json/wp/v2/posts",
                    auth=(settings.wordpress_username, settings.wordpress_app_password),
                    json={
                        "title": content.title,
                        "content": content.body,
                        "excerpt": content.meta_description,
                        "status": "draft",
                        "tags": content.tags,
                    },
                    timeout=15.0,
                )
                if response.status_code == 201:
                    data = response.json()
                    content.published_url = data.get("link", "")
                    content.platform_post_id = str(data.get("id", ""))
                    logger.info(f"Published to WordPress: {content.published_url}")
                    return True
                logger.error(f"WordPress error {response.status_code}: {response.text[:200]}")
                return False
        except httpx.RequestError as e:
            logger.error(f"WordPress publish failed: {e}")
            return False

    async def publish_to_webflow(self, content: GeneratedContent, collection_id: str) -> bool:
        """Publish content to a Webflow CMS collection."""
        if not settings.webflow_api_key:
            logger.warning("Webflow not configured — skipping publish")
            return False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.webflow.com/collections/{collection_id}/items",
                    headers={
                        "Authorization": f"Bearer {settings.webflow_api_key}",
                        "accept-version": "1.0.0",
                    },
                    json={
                        "fields": {
                            "name": content.title,
                            "slug": content.title.lower().replace(" ", "-")[:60],
                            "post-body": content.body,
                            "meta-description": content.meta_description,
                            "_archived": False,
                            "_draft": True,
                        }
                    },
                    timeout=15.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    content.platform_post_id = data.get("_id", "")
                    logger.info(f"Published to Webflow: {content.platform_post_id}")
                    return True
                logger.error(f"Webflow error {response.status_code}")
                return False
        except httpx.RequestError as e:
            logger.error(f"Webflow publish failed: {e}")
            return False


content_agent = ContentSEOAgent()

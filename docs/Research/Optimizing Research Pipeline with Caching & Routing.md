# **Optimizing Research Architectures: A Comprehensive Redesign of the Research Coordinator Pipeline**

## **Executive Summary**

In the rapidly evolving landscape of automated information retrieval, the efficiency of the underlying architecture dictates not only the operational cost but also the user experience. The legacy implementation of the research\_coordinator.py system—characterized by a monolithic, brute-force execution strategy—presents a critical bottleneck in scaling our research capabilities. Currently, the system operates on a naive "fire-and-forget" principle, blindly triggering expensive multi-modal retrieval processes (Web Search and YouTube Data API) for every user query, regardless of complexity or redundancy. This approach has resulted in an unsustainable cost per query of approximately $0.50 and unacceptable latency metrics due to sequential blocking I/O operations.

This report details a comprehensive architectural redesign aimed at transforming this legacy pipeline into an intelligent, state-aware research engine. The proposed solution introduces three fundamental engineering paradigms: **Semantic Caching**, **Intelligent Model Routing**, and **Asynchronous Parallelization**. By implementing a semantic cache layer backed by vector embeddings, the system can identify and intercept redundant queries—such as recognizing that "How to mix 808s" and "808 mixing guide" are semantically equivalent—thereby serving instant results at near-zero cost. For novel queries, a lightweight routing layer utilizing gemini-2.0-flash-lite acts as a cognitive dispatcher, categorizing user intent into "Simple Retrieval," "Complex Technique," or "Specific Fact," and activating only the necessary tools. Finally, the refactoring of sequential await chains into non-blocking asyncio.gather patterns ensures that unavoidable I/O operations are executed concurrently, minimizing total request latency to the duration of the single slowest component.

The following analysis provides a rigorous technical breakdown of each component, supported by code implementations, theoretical frameworks, and performance projections. It demonstrates that this redesign will not only reduce operational costs by an estimated 60-80% for high-traffic workloads but also fundamentally enhance the system's responsiveness and scalability.

## **1\. Problem Definition and Architectural Analysis**

### **1.1 The Legacy Monolith: Anatomy of Inefficiency**

The existing research pipeline represents a classic "Generation 1" AI application structure. In this paradigm, the Large Language Model (LLM) is treated as a universal hammer, and every user interaction is a nail. The logic flow is linear and indiscriminate: upon receiving a query, the system immediately instantiates high-latency network requests to external providers (Google Search, YouTube), awaits their completion one by one, and then passes the aggregated massive context window to an expensive reasoning model for synthesis.

This architecture suffers from three primary failure modes:

1. **Redundant Computation:** The system lacks memory. If ten users ask "What is the capital of France?" in ten minutes, the system performs ten identical web searches and ten identical LLM inference passes. This O(N) cost scaling relative to user volume is financially hazardous.1  
2. **Resource Over-Provisioning:** A query requiring a simple fact check (e.g., "internal server IP address") triggers the same heavy-lifting machinery as a complex research request (e.g., "comparative analysis of sorting algorithms"). Using a "smart" model for "dumb" tasks is a misallocation of GPU resources and budget.2  
3. **Blocking Latency:** The sequential execution pattern (await web \-\> await youtube) ensures that the user waits for the sum of all service latencies (![][image1]). In a distributed system, latency should ideally be governed by the slowest single dependency (![][image2]), not their aggregate.4

### **1.2 The Economic Imperative for Redesign**

The current unit economic model is unsustainable. At \~$0.50 per query, a modest user base of 1,000 daily active users (DAU) generating 5 queries each results in a daily burn rate of $2,500, or roughly $75,000 monthly.

**Table 1: Cost Breakdown of Naive vs. Optimized Architecture (Projected)**

| Component | Naive Cost / Query | Optimized Cost / Query | Logic for Reduction |
| :---- | :---- | :---- | :---- |
| **Orchestration** | $0.00 | $0.005 | Introduction of gemini-2.0-flash-lite router. |
| **Retrieval (Web)** | $0.02 | $0.01 | Reduced volume via caching and routing logic. |
| **Retrieval (Video)** | $0.02 | $0.005 | Only triggered for "Complex Technique" queries. |
| **Synthesis (LLM)** | $0.46 | $0.05 | Expensive model replaced/minimized; cached hits cost $0. |
| **Total** | **\~$0.50** | **\~$0.07** | **\~86% Reduction** |

The transition to an intelligent pipeline is not merely an optimization; it is a requirement for financial viability.

## **2\. Theoretical Framework: Semantic Intelligence in Search**

To address the requirement for "Semantic Caching," we must first establish the theoretical underpinnings of how a machine "understands" that two different strings of text represent the same intent.

### **2.1 Vector Embeddings and High-Dimensional Spaces**

Traditional caching mechanisms, such as Redis, rely on exact string matching (hashing). If the cache key is "how to mix 808s", a query for "mixing 808s tutorial" will result in a cache miss. This is insufficient for natural language interfaces.

Semantic caching utilizes **Vector Embeddings**. An embedding model (such as OpenAI's text-embedding-3-small or open-source equivalents like all-mpnet-base-v2 6) transforms text input into a fixed-size vector of floating-point numbers (e.g., 1,536 dimensions). In this high-dimensional space, semantic meaning is encoded in geometric proximity. Concepts that are semantically similar are mapped to points that are physically closer together in the vector space.7

### **2.2 Cosine Similarity as a Metric**

To quantify "closeness," we employ **Cosine Similarity**. Unlike Euclidean distance, which measures the straight-line distance between points (and can be affected by the magnitude of the vectors, often representing document length), Cosine Similarity measures the cosine of the angle between two vectors.1

The formula for Cosine Similarity between vector ![][image3] and vector ![][image4] is:

![][image5]

* **1.0**: The vectors are identical (angle is 0°).  
* **0.0**: The vectors are orthogonal (angle is 90°, unrelated meanings).  
* **\-1.0**: The vectors are diametrically opposed (angle is 180°).

For our research coordinator, we will define a **similarity threshold** (e.g., 0.90). If an incoming query's vector has a cosine similarity of \>0.90 with a stored query vector, we consider it a "hit" and return the stored response. This allows "How to mix 808s" and "808 mixing guide" to be treated as identical requests.1

## **3\. Component 1: The Semantic Caching Layer**

The first line of defense in our redesigned architecture is the Semantic Cache. This component intercepts user queries before they reach any API-consuming logic.

### **3.1 Storage Strategy: Local Vector Store**

While production systems processing millions of vectors require dedicated databases like ChromaDB, Milvus, or Pinecone, the requirement here calls for a demonstrable implementation. We will architect a modular solution that can operate with a lightweight local JSON store (using NumPy for calculations) while maintaining API compatibility with ChromaDB for future scaling.1

**Architectural Decision:** We will use a "Look-Aside" cache pattern.

1. **Read-Through:** The coordinator asks the cache for the query.  
2. **Hit:** Cache returns data; Coordinator returns immediately.  
3. **Miss:** Coordinator executes research; Coordinator writes result to cache asynchronously.

### **3.2 Implementation: The SemanticCache Class**

The following Python implementation utilizes a local JSON file for persistence and manual Cosine Similarity calculation. This satisfies the requirement for a "simple JSON \+ Cosine Similarity script" while structuring it as a robust class that can be integrated into the research\_coordinator.py.1

Python

import json  
import numpy as np  
import os  
from typing import List, Dict, Optional, Tuple  
from datetime import datetime

\# In a real scenario, import your embedding client (e.g., OpenAI, SentenceTransformers)  
\# from sentence\_transformers import SentenceTransformer

class SemanticCache:  
    """  
    A lightweight semantic cache using local JSON storage and Cosine Similarity.  
    Designed to intercept redundant research queries.  
    """  
    def \_\_init\_\_(self, cache\_file: str \= "semantic\_cache.json", threshold: float \= 0.92):  
        self.cache\_file \= cache\_file  
        self.threshold \= threshold  
        \# self.encoder \= SentenceTransformer('all-mpnet-base-v2') \# Uncomment for real embeddings  
        self.cache\_data \= self.\_load\_cache()

    def \_load\_cache(self) \-\> List:  
        """Loads the cache from disk."""  
        if not os.path.exists(self.cache\_file):  
            return  
        try:  
            with open(self.cache\_file, 'r') as f:  
                return json.load(f)  
        except json.JSONDecodeError:  
            return

    def \_save\_cache(self):  
        """Persists the cache to disk."""  
        with open(self.cache\_file, 'w') as f:  
            json.dump(self.cache\_data, f, indent=2)

    def \_get\_embedding(self, text: str) \-\> List\[float\]:  
        """  
        Generates a vector embedding for the given text.  
        For this report's simulation, we return a normalized random vector.  
        In production, replace with: return self.encoder.encode(text).tolist()  
        """  
        \# Mocking embedding for demonstration purposes  
        \# Utilizing a deterministic seed based on text hash to simulate stability  
        np.random.seed(hash(text) % 2\*\*32)   
        vector \= np.random.rand(768)  
        return (vector / np.linalg.norm(vector)).tolist()

    def \_cosine\_similarity(self, vec\_a: List\[float\], vec\_b: List\[float\]) \-\> float:  
        """Calculates Cosine Similarity between two vectors."""  
        a \= np.array(vec\_a)  
        b \= np.array(vec\_b)  
        if np.linalg.norm(a) \== 0 or np.linalg.norm(b) \== 0:  
            return 0.0  
        return np.dot(a, b) / (np.linalg.norm(a) \* np.linalg.norm(b))

    def lookup(self, query: str) \-\> Optional\[str\]:  
        """  
        Searches the cache for a semantically similar query.  
        Returns the cached response if a match \> threshold is found.  
        """  
        query\_vector \= self.\_get\_embedding(query)  
        best\_score \= \-1.0  
        best\_entry \= None

        print(f"--- Cache Lookup for: '{query}' \---")

        for entry in self.cache\_data:  
            score \= self.\_cosine\_similarity(query\_vector, entry\['vector'\])  
              
            \# Log scores for debugging visibility  
            \# print(f"Checking against: '{entry\['query'\]}' | Score: {score:.4f}")

            if score \> best\_score:  
                best\_score \= score  
                best\_entry \= entry

        if best\_score \>= self.threshold:  
            print(f"✅ CACHE HIT. Matched: '{best\_entry\['query'\]}' (Score: {best\_score:.4f})")  
            return best\_entry\['response'\]  
          
        print(f"❌ CACHE MISS. Nearest neighbor score: {best\_score:.4f}")  
        return None

    def store(self, query: str, response: str):  
        """Stores a new query-response pair in the cache."""  
        vector \= self.\_get\_embedding(query)  
        new\_entry \= {  
            "query": query,  
            "vector": vector,  
            "response": response,  
            "timestamp": datetime.utcnow().isoformat()  
        }  
        self.cache\_data.append(new\_entry)  
        self.\_save\_cache()  
        print(f"💾 Stored result for '{query}' in cache.")

\# Example Usage Simulation  
if \_\_name\_\_ \== "\_\_main\_\_":  
    cache \= SemanticCache()  
      
    \# 1\. First Query (Cache Miss)  
    q1 \= "How to mix 808s"  
    if not cache.lookup(q1):  
        \# Simulate fetching data  
        fake\_response \= "To mix 808s, use saturation, sidechain compression, and EQ."  
        cache.store(q1, fake\_response)  
      
    \# 2\. Second Query (Semantically Similar \- Should Hit)  
    q2 \= "808 mixing guide"   
    \# Note: With random mock embeddings, this won't mathematically match,   
    \# but logically this is the flow. In a real system, vectors for q1 and q2 would be close.  
    result \= cache.lookup(q2)

### **3.3 Insight: The "Memory" Effect**

Implementing this layer fundamentally changes the nature of the research tool. It evolves from a stateless functional pipeline into a system with "memory." Over time, the vector store accumulates a knowledge base specific to the user's domain. This has second-order implications for **personalization**: future iterations could weight the similarity search not just by query content, but by user preference vectors, effectively prioritizing results that align with the user's past successful interactions.11

However, this introduces the challenge of **Cache Invalidation**. Unlike data in a database, research results expire. A cached answer for "NVIDIA stock price" is valid for minutes; "How to mix 808s" is valid for years. The timestamp field in the store method is crucial here. The lookup logic can be enhanced to check max\_cache\_age\_hours based on the query type (e.g., News \= 1 hour, Tutorials \= 1 year).10

## **4\. Component 2: Intelligent Model Routing**

When the cache returns a miss, the system must decide *how* to research the topic. The naive system's flaw is treating all misses equally. The optimized system introduces a "Brain" (Router) to classify intent.

### **4.1 Selection of the Classifier: Gemini 2.0 Flash-Lite**

For the routing layer, we require a model that is extremely fast (low Time-To-First-Token) and extremely cheap, as it will run on every non-cached query. We have selected **Gemini 2.0 Flash-Lite** for this role.

* **Latency:** It is optimized for high-throughput, low-latency tasks, making it ideal for middleware classification where every millisecond of delay blocks the user.12  
* **Cost Efficiency:** It is significantly cheaper than "Pro" or "Thinking" models, allowing us to maintain the "Orchestration" cost line item at negligible levels.14  
* **Structured Output:** A critical requirement for programmatic routing is reliable output. We cannot parse free text. Gemini 2.0 supports response\_schema natively, allowing us to enforce a Pydantic schema for the routing decision.12

### **4.2 The Taxonomy of Intent**

We define three distinct research strategies based on the user's intent. This taxonomy covers the spectrum of information retrieval needs.2

**Table 2: Research Intent Categories and Routing Logic**

| Category | Intent Description | Tooling Strategy | Why? |
| :---- | :---- | :---- | :---- |
| **Simple Retrieval** | Queries for singular facts, recent news events, weather, stock prices, or surface-level definitions. | web\_search Only | YouTube is noisy and inefficient for simple facts. Reasoning models are overkill. |
| **Complex Technique** | Procedural "How-to" requests, tutorials, deep dives into skills, educational content, or multi-faceted analysis. | web\_search \+ youtube\_search | Video content is often superior for procedural learning (e.g., coding, cooking, music production). |
| **Specific Fact** | Queries referencing internal proprietary data, company acronyms, project codes, or specific codified knowledge. | internal\_kb Only | Public web search will hallucinate or fail on private data. Security requires isolating this path. |

### **4.3 Implementation: The ResearchPolicy Class**

This class encapsulates the routing logic. It interacts with the Gemini API to classify the query and returns a RoutePlan object. We use Pydantic to define the strict schema, ensuring the LLM never returns malformed JSON.16

Python

import os  
from enum import Enum  
from typing import List, Optional  
from pydantic import BaseModel, Field  
\# Assuming usage of google-genai SDK  
\# from google import genai

class ResearchCategory(str, Enum):  
    SIMPLE \= "Simple Retrieval"  
    COMPLEX \= "Complex Technique"  
    SPECIFIC \= "Specific Fact"

class RoutePlan(BaseModel):  
    category: ResearchCategory \= Field(..., description="The classified category of the user's request.")  
    reasoning: str \= Field(..., description="A brief explanation of why this category was chosen.")  
    tools: List\[str\] \= Field(..., description="The list of tools strictly required for this category.")  
    search\_queries: List\[str\] \= Field(..., description="Optimized search queries to use for the tools.")

class ResearchPolicy:  
    """  
    The decision-making engine of the pipeline.  
    Uses Gemini 2.0 Flash-Lite to categorize user intent.  
    """  
    def \_\_init\_\_(self, api\_key: str):  
        self.api\_key \= api\_key  
        \# self.client \= genai.Client(api\_key=api\_key) \# Initialize Gemini Client  
        self.model\_id \= "gemini-2.0-flash-lite"

    async def determine\_route(self, user\_query: str) \-\> RoutePlan:  
        """  
        Classifies the user query into a research strategy.  
        """  
        print(f"🤔 Routing Query via {self.model\_id}...")  
          
        system\_instruction \= """  
        You are an expert Research Coordinator. Your task is to analyze the user's query and route it to the most efficient data sources.  
          
        CLASSIFICATION RULES:  
        1\. Simple Retrieval: Quick facts, news, definitions, surface-level info. Tool: \['web\_search'\].  
        2\. Complex Technique: Tutorials, how-to guides, deep learning, skill acquisition, or multi-modal synthesis. Tools: \['web\_search', 'youtube\_search'\].  
        3\. Specific Fact: Internal company data, proprietary knowledge, project codes, employee details. Tool: \['internal\_kb'\].

        OUTPUT:  
        Return a strict JSON object matching the RoutePlan schema.   
        Generate 1-2 optimized search queries based on the intent.  
        """

        \# Mocking the API call for this report simulation  
        \# In production:  
        \# response \= await self.client.models.generate\_content\_async(  
        \#     model=self.model\_id,  
        \#     contents=user\_query,  
        \#     config={  
        \#         "response\_mime\_type": "application/json",  
        \#         "response\_schema": RoutePlan,  
        \#         "system\_instruction": system\_instruction  
        \#     }  
        \# )  
        \# return response.parsed

        \# Simulation Logic based on keywords to demonstrate flow  
        lower\_q \= user\_query.lower()  
        if "mix" in lower\_q or "tutorial" in lower\_q or "guide" in lower\_q:  
            return RoutePlan(  
                category=ResearchCategory.COMPLEX,  
                reasoning="Query implies procedural knowledge acquisition best served by video and text.",  
                tools=\["web\_search", "youtube\_search"\],  
                search\_queries=\[user\_query, f"{user\_query} tutorial"\]  
            )  
        elif "internal" in lower\_q or "schedule" in lower\_q or "q3" in lower\_q:  
            return RoutePlan(  
                category=ResearchCategory.SPECIFIC,  
                reasoning="Query requests proprietary/internal information.",  
                tools=\["internal\_kb"\],  
                search\_queries=\[user\_query\]  
            )  
        else:  
            return RoutePlan(  
                category=ResearchCategory.SIMPLE,  
                reasoning="Query seeks general factual information available on the public web.",  
                tools=\["web\_search"\],  
                search\_queries=\[user\_query\]  
            )

## **5\. Component 3: Asynchronous Parallelization**

The final piece of the redesign addresses the latency bottleneck. The legacy system's sequential await pattern effectively serialized operations that had no interdependencies.

### **5.1 The Physics of I/O Bound Concurrency**

In Python, the Global Interpreter Lock (GIL) prevents CPU-bound tasks from running in parallel on a single thread. However, network requests (API calls) are **I/O bound**. When an await keyword is encountered for a network request, the event loop releases the control, allowing other tasks to run.

By switching from sequential await to asyncio.gather, we schedule all necessary API calls on the event loop simultaneously.

* **Sequential Time:** ![][image6]  
* **Parallel Time:** ![][image7] (where ![][image8] is overhead)

### **5.2 Handling Failures in Parallel Streams**

A robust distributed system must handle partial failure. If the YouTube API is down or rate-limited, the Web Search should still proceed. asyncio.gather provides the return\_exceptions=True parameter. This ensures that if one task raises an Exception, it is caught and returned in the results list, rather than crashing the entire gathering process.18

### **5.3 Implementation: The Refactored ResearchCoordinator**

This module integrates the Cache and Policy to execute the research.

Python

import asyncio  
from typing import List, Any

\# Mocking external tools  
async def search\_web(query: str) \-\> str:  
    print(f"    🌐 Searching Web for: {query}")  
    await asyncio.sleep(1.5) \# Simulate 1.5s latency  
    return f"Web Results: Top hits for {query}..."

async def search\_youtube(query: str) \-\> str:  
    print(f"    📺 Searching YouTube for: {query}")  
    await asyncio.sleep(2.0) \# Simulate 2.0s latency  
    return f"YouTube Results: Video guide for {query}..."

async def search\_internal\_kb(query: str) \-\> str:  
    print(f"    🗄️  Searching Internal KB for: {query}")  
    await asyncio.sleep(0.5) \# Simulate 0.5s latency (faster internal network)  
    return f"Internal KB: Confidential document regarding {query}..."

class ResearchCoordinator:  
    def \_\_init\_\_(self, cache: SemanticCache, policy: ResearchPolicy):  
        self.cache \= cache  
        self.policy \= policy

    async def execute\_research(self, user\_query: str) \-\> str:  
        print(f"\\n🚀 STARTING RESEARCH: '{user\_query}'")  
          
        \# 1\. Semantic Cache Check  
        cached\_result \= self.cache.lookup(user\_query)  
        if cached\_result:  
            return f"\\n{cached\_result}"

        \# 2\. Intelligent Routing  
        plan \= await self.policy.determine\_route(user\_query)  
        print(f"📋 PLAN: {plan.category.value} | Tools: {plan.tools}")

        \# 3\. Parallel Execution via asyncio.gather  
        tasks \=  
          
        \# Dispatch tasks based on the plan  
        \# Note: We use the optimized search queries generated by the router  
        primary\_query \= plan.search\_queries  
          
        if "web\_search" in plan.tools:  
            tasks.append(search\_web(primary\_query))  
          
        if "youtube\_search" in plan.tools:  
            tasks.append(search\_youtube(primary\_query))  
              
        if "internal\_kb" in plan.tools:  
            tasks.append(search\_internal\_kb(primary\_query))

        \# EXECUTE PARALLEL FETCH  
        print(f"⚡ Firing {len(tasks)} tasks in parallel...")  
        raw\_results \= await asyncio.gather(\*tasks, return\_exceptions=True)

        \# 4\. Result Synthesis & Error Handling  
        synthesized\_data \= self.\_process\_results(raw\_results, plan)  
          
        \# 5\. Update Cache  
        self.cache.store(user\_query, synthesized\_data)

        return synthesized\_data

    def \_process\_results(self, results: List\[Any\], plan: RoutePlan) \-\> str:  
        """  
        Combines results, filtering out failed tasks.  
        """  
        valid\_content \=  
        errors \=

        for res in results:  
            if isinstance(res, Exception):  
                errors.append(str(res))  
            else:  
                valid\_content.append(res)

        if not valid\_content:  
            return "Research failed. All tools returned errors."

        \# In a real app, you might send this content back to the LLM for final summarization.  
        \# Here we just format it.  
        final\_output \= f"--- Research Report: {plan.category.value} \---\\n"  
        final\_output \+= f"Reasoning: {plan.reasoning}\\n\\n"  
        final\_output \+= "\\n\\n".join(valid\_content)  
          
        if errors:  
            final\_output \+= f"\\n\\n: Some tools failed: {', '.join(errors)}"

        return final\_output

## **6\. End-to-End System Integration Example**

To demonstrate the efficacy of the redesign, we simulate the pipeline processing the user's specific query examples.

### **6.1 Scenario 1: "How to mix 808s" (First Run)**

1. **Cache:** Miss.  
2. **Router:** Analysis detects "mix" and procedural intent. Classifies as **Complex Technique**.  
3. **Plan:** Tools \= \[web\_search, youtube\_search\].  
4. **Execution:** search\_web (1.5s) and search\_youtube (2.0s) launch simultaneously.  
5. **Latency:** Total wait is \~2.0s (bounded by YouTube).  
6. **Result:** User gets a mix of articles and video guides. Result stored in Cache.

### **6.2 Scenario 2: "How to mix 808s" (Second Run)**

1. **Cache:** Hit (Exact match or high similarity).  
2. **Execution:** Return stored JSON immediately.  
3. **Latency:** \~0.05s.  
4. **Cost:** $0.00.

### **6.3 Scenario 3: "Internal Q3 Deployment Schedule"**

1. **Cache:** Miss.  
2. **Router:** Analysis detects "Internal" and "Schedule". Classifies as **Specific Fact**.  
3. **Plan:** Tools \= \[internal\_kb\].  
4. **Execution:** Only search\_internal\_kb is called. Public web APIs are **not** touched.  
5. **Security:** Internal data is not leaked to public search prompts; public noise does not pollute the answer.

## **7\. Performance Benchmarking and Future Outlook**

### **7.1 Quantitative Analysis**

Applying Amdahl's Law to our latency reduction:

If the sequential part of the program (Orchestration/Routing) takes 5% of the time, and the parallelizable part (Retrieval) takes 95%, parallelization offers massive speedups.

* **Original:** Routing (0s) \+ Web (1.5s) \+ YouTube (2.0s) \= **3.5s**  
* **New:** Routing (0.3s) \+ Max(Web 1.5s, YouTube 2.0s) \= **2.3s**  
  * *Improvement:* \~34% faster for complex queries.  
  * *Improvement:* \~99% faster for cached queries.

### **7.2 Scalability and Migration to ChromaDB**

As the dataset grows beyond 10,000 queries, the linear scan (![][image9]) in our JSON SemanticCache will become a bottleneck. The architecture allows for a seamless swap to **ChromaDB**. Chroma uses **HNSW (Hierarchical Navigable Small World)** graphs to perform Approximate Nearest Neighbor (ANN) search in logarithmic time (![][image10]).6

To migrate, the SemanticCache class lookup method would simply change from iterating a list to calling collection.query(query\_embeddings=\[vec\], n\_results=1). This future-proofing ensures the system remains viable as it scales to enterprise levels.

## **8\. Conclusion**

The transition from the legacy "naive" pipeline to this engineered "Router-Solver" architecture represents a maturation of the AI research tool. By respecting the heterogeneity of user requests—acknowledging that a request for a stock price differs fundamentally from a request for a tutorial—we optimize resource allocation. The introduction of **Semantic Caching** creates a system that learns and becomes more efficient with use, rather than one that perpetually repeats its work. The adoption of **Asyncio** ensures that the system's speed is limited only by external network physics, not internal mismanagement.

This redesign not only solves the immediate financial bleeding ($0.50/query \-\> \~$0.07/query) but establishes a robust, extensible foundation for future capabilities, such as personalized re-ranking and multi-agent collaboration. The system is no longer just a script; it is a scalable platform.

#### **Works cited**

1. Semantic Caching and Memory Patterns for Vector Databases ..., accessed February 10, 2026, [https://www.dataquest.io/blog/semantic-caching-and-memory-patterns-for-vector-databases/](https://www.dataquest.io/blog/semantic-caching-and-memory-patterns-for-vector-databases/)  
2. Bringing intelligent, efficient routing to open source AI with vLLM Semantic Router \- Red Hat, accessed February 10, 2026, [https://www.redhat.com/en/blog/bringing-intelligent-efficient-routing-open-source-ai-vllm-semantic-router](https://www.redhat.com/en/blog/bringing-intelligent-efficient-routing-open-source-ai-vllm-semantic-router)  
3. Beyond Basic RAG: Improving Your Knowledge Agents with Intent-Driven Architectures, accessed February 10, 2026, [https://promptql.io/blog/beyond-basic-rag-promptqls-intent-driven-solution-to-query-inefficiencies](https://promptql.io/blog/beyond-basic-rag-promptqls-intent-driven-solution-to-query-inefficiencies)  
4. python 3.x \- Asyncio gather difference \- Stack Overflow, accessed February 10, 2026, [https://stackoverflow.com/questions/73988859/asyncio-gather-difference](https://stackoverflow.com/questions/73988859/asyncio-gather-difference)  
5. Mastering Python asyncio.gather and asyncio.as\_completed for LLM ..., accessed February 10, 2026, [https://python.useinstructor.com/blog/2023/11/13/learn-async/](https://python.useinstructor.com/blog/2023/11/13/learn-async/)  
6. Implementing semantic cache to improve a RAG system with FAISS ..., accessed February 10, 2026, [https://huggingface.co/learn/cookbook/semantic\_cache\_chroma\_vector\_database](https://huggingface.co/learn/cookbook/semantic_cache_chroma_vector_database)  
7. 6\. Semantic Search with ChromaDB \- Go Beyond Keywords Using Embeddings \- YouTube, accessed February 10, 2026, [https://m.youtube.com/watch?v=NVJ6rfQuwAY](https://m.youtube.com/watch?v=NVJ6rfQuwAY)  
8. Semantic Cache: How to Speed Up LLM and RAG Applications \- Medium, accessed February 10, 2026, [https://medium.com/@svosh2/semantic-cache-how-to-speed-up-llm-and-rag-applications-79e74ce34d1d](https://medium.com/@svosh2/semantic-cache-how-to-speed-up-llm-and-rag-applications-79e74ce34d1d)  
9. Implementing Cosine Similarity in Python \- Tiger Data, accessed February 10, 2026, [https://www.tigerdata.com/learn/implementing-cosine-similarity-in-python](https://www.tigerdata.com/learn/implementing-cosine-similarity-in-python)  
10. How to Build Semantic Caching \- OneUptime, accessed February 10, 2026, [https://oneuptime.com/blog/post/2026-01-30-llmops-semantic-caching/view](https://oneuptime.com/blog/post/2026-01-30-llmops-semantic-caching/view)  
11. Implementing Semantic Caching: A Step-by-Step Guide to Faster, Cost-Effective GenAI Workflows | by Arun Shankar | Google Cloud \- Medium, accessed February 10, 2026, [https://medium.com/google-cloud/implementing-semantic-caching-a-step-by-step-guide-to-faster-cost-effective-genai-workflows-ef85d8e72883](https://medium.com/google-cloud/implementing-semantic-caching-a-step-by-step-guide-to-faster-cost-effective-genai-workflows-ef85d8e72883)  
12. Gemini 2.0 Flash-Lite | Generative AI on Vertex AI \- Google Cloud Documentation, accessed February 10, 2026, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-0-flash-lite](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-0-flash-lite)  
13. Gemini 2.0 Flash Lite \- API, Providers, Stats \- OpenRouter, accessed February 10, 2026, [https://openrouter.ai/google/gemini-2.0-flash-lite-001](https://openrouter.ai/google/gemini-2.0-flash-lite-001)  
14. Gemini 2.0 model updates: 2.0 Flash, Flash-Lite, Pro Experimental \- Google Blog, accessed February 10, 2026, [https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-model-updates-february-2025/](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/gemini-model-updates-february-2025/)  
15. Structured outputs | Gemini API \- Google AI for Developers, accessed February 10, 2026, [https://ai.google.dev/gemini-api/docs/structured-output](https://ai.google.dev/gemini-api/docs/structured-output)  
16. gemini-samples/examples/gemini-structured-outputs.ipynb at main \- GitHub, accessed February 10, 2026, [https://github.com/philschmid/gemini-samples/blob/main/examples/gemini-structured-outputs.ipynb](https://github.com/philschmid/gemini-samples/blob/main/examples/gemini-structured-outputs.ipynb)  
17. Structured output \- Gemini by Example, accessed February 10, 2026, [https://geminibyexample.com/020-structured-output/](https://geminibyexample.com/020-structured-output/)  
18. Exception handling in asyncio \- Piccolo Blog, accessed February 10, 2026, [https://piccolo-orm.com/blog/exception-handling-in-asyncio/](https://piccolo-orm.com/blog/exception-handling-in-asyncio/)  
19. Asyncio gather() Handle Exceptions \- Super Fast Python, accessed February 10, 2026, [https://superfastpython.com/asyncio-gather-exception/](https://superfastpython.com/asyncio-gather-exception/)

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAZCAYAAADuWXTMAAABT0lEQVR4Xo1SsUoEQQzNgNddI4KcaGFhLyhXXGElllrYeh9gbSP4GdcpWPgZNmIrFiL4A4JfINyB1fmyye4mMxm9B28z8yZvkuwukSK1C4NIK5H6xJUMJv9fSKJ3hOZQJBqAx+B2s1ulshllirAET91B9Y5e3gQ/SMxXlWwL19eLks0PnVqgvJZnnUK+ITWbUUzIllr8DKsheE1iftZ9YPbYAJ94gYxzPBtz8mYPFfdIquyqPAYX4Be4w0Jv9tesQbhDvDTaIThX8tpbmo0oR+APyYw5ufq4VnaI3SPiSdbNFvI+qf1RUt6sgFu9J/lEFuvgK7iE6SKvPMDzAPGN2v/XY0Ty5rnyrT3Yh/879XPxvBNz+7vo+FSpy5mFY9tZirlaIXeWemA2KM9SflUdefEY3ZlP0l3F+dccXYcZKrmF5tCIUVakhbDtmMTIz/EXs5wxsdksrLUAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAABjUlEQVR4Xo1UsUoEQQydoIVwoojXWNjYCXaC/oBfYGdjY6GFvV/gD4iVYmlna3eIvYU2ViKIjdVxCHelrC+ZzGwmsyu+420mL9k3md1jQ2CQXCPS2mhEVPaI5hJXr/L/Qe9qh+BfSuxoXfZ+xMJGQtVTg8ImLrfgO7JP5Qt4A14x4XGEuBQNjaMZlrGH9BVx6Lbl5BJswFVbyND2c6zuEOdLA1mfIbLBtikUWADv0XScldaDB9UJaJjVXI2NG+BXkB3InSDsgBPwp1AtSMaXM14jkQcX4kP8AA/BgTMtNlkEH/WMa2SI/Bn8xvoAcS6264TJABGvMYyxGifRmK9j/cbmiCeupqBwobtz9NUBONI6x6plBY/4KcTz7+dqbqIt1Cc6wWlSLfi9zoIcQY6iyA4PIZqPoCxHPdb03FJk9wZ6g1cquXIK7gb3d40wUuvZj+I7oJIXFH16qrhxutq9Jl8mq/uGWmBQj27xV4PWusZtQ9cmSXAFTqNU3cFShygwnzXNq9fRpuXWPYNk/ALQNTgs33DloAAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAYCAYAAADH2bwQAAAA1ElEQVR4XnVSsQ3CQAx8FxRUIKWiRWIEKsZgGGoGyQI0tOzAADQ0bEGDxL3P9jtPsPK+O/tkf5SUUkQfDXEyq5PRtEpJrspqWTGbm4mopomLs4y7yfmsiSlv8aoxoezfitGmpPacM9c46gJ8A89QO+AQLuQVmh+QY97blhU5IV1xFqrCwtjgvHD2cTOFmihokLJt071JscS5iU6IAV1w1AP5ie4Ifkfh4N1sG7C7rlxzlPcM8xUahKlezFDBND0Uk2+TeYQ7+l0/d+h4ivaT/DU4OvsC/18MQVC6ayQAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAZCAYAAAB3oa15AAADxElEQVR4Xq1XW6tNURQeMxS5XyJRHJ1OKUUJkScpyiU5HuT8AC+iKCd5UVLKi0RJSh6kpDy4hnJ7OeVJEYmSdJSSUhTi+L451lx7rjnH2mud+Orba+8xvznmGGPe1hYRJ/8bzR6bFf8VzcMFRY2yxmyjvbhQRoO36tsgcjIOnzNS8z+A/qamxkaUYTqZhs+54JisMc+FA10D+/kjb07RrBD1eUm6iu2mM+BXcBjN7/H8DZ6CeEpVpnA60G3wkP5M4e6L+iFf0VBtl8PgRfBcxGVF20zwgOR9TEwAT4DHRTsGbEDvL3i+Bnu9peruIDgEm/bJh9oB7oP5O54j4JJEtAbcC34Ev4GbwIlROxNfGf2OoH7mg09FK+2XgIHpQo3zAcTj89tLcE5psYEZlN3gEbH1s8AH4OLEzgE24vFT9JlAA7kuWpmTpSXHWPCqqC7GPNHgOsg8uMn4uAEuF19972NPRSKyFnwkWqgUTO4FeFk0jhRuBIMOS1geBpyGdamYgfFR01ZwuxG1RDZW9Zb44BwDoI8hqZ4wnJ1KISKPOrbIO9GCVTDHJyByWuwoAiaBD40EjoFL/bf63gPgBekofoB/pLMkmNQV0WLUYRD8JTpTFTBrbp5FaQMRxUTnDD7eA5qUPe0xWP1ibTt2xYz5BJjIanA9eFfor74I1LAPEynBnc4j7gk6cp1m8P78mH6GGPyHqDkkwGc33JNqklw6XEJh5hkUZ7IbuH94QlUSCAGQk+qTl160cY9wwKPeouIQSFMCfm0H/8WTm5j+hmHgBcgKd4FbDl2WQNgcD6V7EDydMJh7jufsyN5mBjgGl0wC1yM6m0ziiYTNWV/FFaL3yGCk8d+QkeMRNUvtul46zR68H3iRrUwGCAmkZ3oHzh+Bfv1nsTl/JzCBm1I9GAyxbBHV7jfafIC8ZRdENr7/7BJdd32lNe+8X9KTQTXs34fvj0WP57ynnj4825OTxZL6PfJZqhedC9rN4CfxU+TOihe7N4VtwPRXdvWnCM/wGLTxhAmnll1lBbWcpRr4UcJM3xF93THBinGn7wS3gQslKoWVQwFuZA0uErXpOAqw6qx+entbsEe0rSXofEmTqKE5g+r9JwPnhu+JmmM0uG4op9M3xbfgKlsxCuQOaOFd1e2PTd7L2yyzR7Wh+MW32GdSPQhMlJW1/Adbp63fBZ+W3kKpa9uhg3VS3KhWV8vmUT8gX2/Op0YDNdWw0Fbn0VKcyUYRT1s0+2tWKKKLshZxAuGLPpv7SktRhmqvbr8Ukc1qtpDo/gKNUJTlMunrswAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEwAAAAZCAYAAACb1MhvAAAFVElEQVR4XsWYXchmUxTH185MjcY3kdC8hFIkaUbKlaZ8zUi4kI8rF+NirshMSI005SOaJkpKei+QTLkYzIh4MyVxM1NEMhfeRBRKEWJYv7POfs4+a+99nvO872v86/+c56y19t5rr7322vt5RJaA4AUlVI2iomxQlhqGdLNhhp5mMM3Qb+t78u9ekuv/M7ihutcRPowwWRrqHa9WnuKFQw1mw0r1U8WJYnMYwLAPJynPVB7Tk5bbMNjrylu84n9D2c8h3KB81wvH4FnlL8pvlYvKv5W7lSekRgkI1j7lA2JubgzWDv6ZGh4FrFF+oVxsfXgDoduarymfT3i/ck1rc6dynX31yFfgWOWTyseUpybya5Q/K79Unp/II7YpP5KuzVnKO5SfKf+JRkcJq5S3Kt8SGxv6maJ/pdW9p7ykUwW2JEHstqZvrThbhZ+IZVJtS52sxMYHgO4+V57h5GC7RPvCoBmm2kw1iLhI+b5yg/Ib5da+usEWsV1Twv6WJFBp1LA32MR2haK+ASu3R/KAkU21gbuANah1bRjWgukWLW5WvihWe5+RfEHjXNgFJRDMP5RXekUEk6JeNdut4hbil8RsqRMRN4o5WMJ2FiLtr/3OQ7dv4EA5PVF7rFbLOFHaXCi2naaBBYzBuFzM59s6tZwmloFkYgnrlb+JLXgGHKJDVqISK0FznH4uiAuYNtipvDS+O7gMa8AYh8X6olbw3NTKowlXE2oMTi+q5mOxE/gD5ddiEx7CO2KBAmQTPuzXfpotprhKrMYxpwST5WQhGWdPsPYJQrMa3ynP6ysykEkMnAYgBpH61oeN7QPGJH6VpjaENELUCw6Vy9r3I2LH+1peQtfP7oElTeFLxIJYexaBAOwVm08NJMSbYkEjeBOsVQdw7ID6cXyqcMBNMpBBKaIRMWDllZLgA8ZEfMaBeTH5zvad79SYVS7w2GVwMeTV1ya2I+1ZlIuVByRJkMoaMFYWsDhh6CbdA7WNGsegj3biwP2L60StbRowsoXFKQXsQe0LOavK6jIxTuSYuaqnXbiHl8oEDaHZrr42UXYo/NF/tndah6XQazFgWFHIF6Q3acS9LbNLbLBPpV+k+xmWjdkLWFoDPcyObA9NYJ8S25YPCVceC+A+4YKcj9HBdOtDebfskG6HFIt5ghiXLGBAGwcumEOFlPsZTm9wDscgxJPMY8SWbDqc1wfyWHu4nV+vfFgs6/jJ0v95VgdXghLOFQsW42x0Oo84r8PSndI9EBBu8esSGQ7eLlakOc5ruFfs1PHgpkym4GCcLNHZpp93t9+j7C/lfYmMbc5PqoPKF8RO00fETuNajjFJgvW7mjTbrWDIvYr7lTv5MlDfOAhtAScddT1uUv4gdow/F6z4ftXKfAH1wIktzrnNwQKVcnOrw5S+vxc7HXle18oj+G3n20fyO7AHbfhqq4s8EspZRKA4KYvRTMAJShJd6xUpyAKOfU6Um5Rz0itjVVD4Y7GeBfGfEJ4pGPMnsayN4/OcU74sVtumTbhBYzJgV1K1MjKLQ8K2Y8mwiJ4hL9WWP4od1xNULQtwtjg53xdNwAGQXmtmxzjHCNYOLxyHoQE6HT9yub1fMZEsDx+KbVuynSBdoHxarGQ8Phk4DLuXY5T1nNT/gKhhVMceDHJIqv8lTUF/8pQHDX54QuzuRo2ioJ/TmZTR93zmeVBe3pbpDafphy0S3dXS3dYl1YRSB5ksExQwHBL/XkXRMPC/3l1euny0gxXHHI3lta43ryqWjKzHTLBiWLmem56q3bnjvGqXYGIzxriCvKmX+Pdp6OxnbbkUrEQMhvAvAzP3kzq7fE0AAAAASUVORK5CYII=>
\# System Architecture



ResearchFlow uses a client-server architecture.



\## Components



\### Frontend

\- React

\- Provides the user interface for paper search, research library, paper details, filtering, sorting, and AI summary display.



\### Backend

\- Python

\- FastAPI

\- Handles API requests from the frontend, communicates with external services, processes paper data, and manages database operations.



\### Database

\- SQLite

\- Stores papers, collections, and AI-generated summaries.



\### Academic Data Source

\- OpenAlex API

\- Provides academic paper metadata and abstracts.



\### AI Service

\- OpenRouter API

\- Uses an LLM to extract structured information from paper abstracts.



\### Local Cache

\- JSON files

\- Stores OpenAlex search results to reduce dependency on the external API.



\## Architecture



React Frontend

&#x20;     |

&#x20;     | HTTP / REST

&#x20;     v

FastAPI Backend

&#x20;  |       |        |

&#x20;  |       |        |

&#x20;  v       v        v

SQLite  OpenAlex   OpenRouter

&#x20;          |

&#x20;          v

&#x20;      JSON Cache


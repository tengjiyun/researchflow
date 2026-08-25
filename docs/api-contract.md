\# API Contract



Base URL:



`/api`



\## 1. Search Papers



\### Request



`GET /api/papers/search`



Query parameters:



\- `q`: search keyword

\- `page`: optional page number



Example:



`GET /api/papers/search?q=artificial%20intelligence`



\### Response



```json

{

&#x20; "papers": \[

&#x20;   {

&#x20;     "openalex\_id": "https://openalex.org/W123456789",

&#x20;     "title": "Example Paper",

&#x20;     "authors": \[

&#x20;       "Author One",

&#x20;       "Author Two"

&#x20;     ],

&#x20;     "year": 2025,

&#x20;     "abstract": "Example abstract.",

&#x20;     "doi": "https://doi.org/10.xxxx/example",

&#x20;     "venue": "Example Journal",

&#x20;     "citation\_count": 120,

&#x20;     "url": "https://doi.org/10.xxxx/example"

&#x20;   }

&#x20; ]

}

```



\## 2. Save Paper



\### Request



`POST /api/papers`



```json

{

&#x20; "openalex\_id": "https://openalex.org/W123456789",

&#x20; "title": "Example Paper",

&#x20; "authors": \[

&#x20;   "Author One",

&#x20;   "Author Two"

&#x20; ],

&#x20; "year": 2025,

&#x20; "abstract": "Example abstract.",

&#x20; "doi": "https://doi.org/10.xxxx/example",

&#x20; "venue": "Example Journal",

&#x20; "citation\_count": 120,

&#x20; "url": "https://doi.org/10.xxxx/example"

}

```



\### Response



```json

{

&#x20; "id": 1,

&#x20; "openalex\_id": "https://openalex.org/W123456789",

&#x20; "title": "Example Paper",

&#x20; "authors": \[

&#x20;   "Author One",

&#x20;   "Author Two"

&#x20; ],

&#x20; "year": 2025,

&#x20; "abstract": "Example abstract.",

&#x20; "doi": "https://doi.org/10.xxxx/example",

&#x20; "venue": "Example Journal",

&#x20; "citation\_count": 120,

&#x20; "url": "https://doi.org/10.xxxx/example"

}

```



\## 3. Get Saved Papers



\### Request



`GET /api/papers`



\### Response



```json

{

&#x20; "papers": \[

&#x20;   {

&#x20;     "id": 1,

&#x20;     "openalex\_id": "https://openalex.org/W123456789",

&#x20;     "title": "Example Paper",

&#x20;     "authors": \[

&#x20;       "Author One",

&#x20;       "Author Two"

&#x20;     ],

&#x20;     "year": 2025,

&#x20;     "abstract": "Example abstract.",

&#x20;     "doi": "https://doi.org/10.xxxx/example",

&#x20;     "venue": "Example Journal",

&#x20;     "citation\_count": 120,

&#x20;     "url": "https://doi.org/10.xxxx/example"

&#x20;   }

&#x20; ]

}

```



\## 4. Get Paper



\### Request



`GET /api/papers/{id}`



\### Response



```json

{

&#x20; "id": 1,

&#x20; "openalex\_id": "https://openalex.org/W123456789",

&#x20; "title": "Example Paper",

&#x20; "authors": \[

&#x20;   "Author One",

&#x20;   "Author Two"

&#x20; ],

&#x20; "year": 2025,

&#x20; "abstract": "Example abstract.",

&#x20; "doi": "https://doi.org/10.xxxx/example",

&#x20; "venue": "Example Journal",

&#x20; "citation\_count": 120,

&#x20; "url": "https://doi.org/10.xxxx/example"

}

```



\## 5. Delete Paper



\### Request



`DELETE /api/papers/{id}`



\### Response



```json

{

&#x20; "message": "Paper deleted successfully"

}

```



\## 6. Generate AI Summary



\### Request



`POST /api/papers/{id}/summary`



\### Response



```json

{

&#x20; "id": 1,

&#x20; "paper\_id": 1,

&#x20; "research\_problem": "Example research problem",

&#x20; "methodology": "Example methodology",

&#x20; "key\_findings": "Example key findings",

&#x20; "limitations": "Example limitations"

}

```



\## 7. Get AI Summary



\### Request



`GET /api/papers/{id}/summary`



\### Response



```json

{

&#x20; "id": 1,

&#x20; "paper\_id": 1,

&#x20; "research\_problem": "Example research problem",

&#x20; "methodology": "Example methodology",

&#x20; "key\_findings": "Example key findings",

&#x20; "limitations": "Example limitations"

}

```



\## Error Response



```json

{

&#x20; "detail": "Error message"

}

```


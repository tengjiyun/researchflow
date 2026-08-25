\# Data Model



\## Paper



Represents an academic paper retrieved from OpenAlex.



| Field | Type | Description |

|---|---|---|

| id | integer | Internal database ID |

| openalex\_id | string | OpenAlex work ID |

| title | string | Paper title |

| authors | list\[string] | Authors of the paper |

| year | integer | Publication year |

| abstract | string or null | Reconstructed paper abstract |

| doi | string or null | DOI |

| venue | string or null | Journal or conference name |

| citation\_count | integer | Number of citations |

| url | string or null | Original paper link |



\## AISummary



Represents structured information extracted from a paper abstract by the LLM.



| Field | Type | Description |

|---|---|---|

| id | integer | Internal database ID |

| paper\_id | integer | ID of the related Paper |

| research\_problem | string | Research problem extracted from the abstract |

| methodology | string | Methodology extracted from the abstract |

| key\_findings | string | Key findings extracted from the abstract |

| limitations | string | Limitations extracted from the abstract |


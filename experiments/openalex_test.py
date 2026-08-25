import requests
def reconstruct_abstract(inverted_index):
    if inverted_index is None:
        return None

    words = []

    for word, positions in inverted_index.items():
        for position in positions:
            words.append((position, word))

    words.sort()

    return " ".join(word for position, word in words)

url = "https://api.openalex.org/works"

params = {
    "search": "artificial intelligence",
    "per_page": 3,
    "select": "id,doi,title,publication_year,authorships,primary_location,cited_by_count,abstract_inverted_index"
}

response = requests.get(url, params=params)

print("Status code:", response.status_code)

data = response.json()

print("Number of results:", len(data["results"]))
print("First paper title:", data["results"][0]["title"])
first_paper = data["results"][0]

abstract = reconstruct_abstract(
    first_paper["abstract_inverted_index"]
)

print("Abstract:")
print(abstract)
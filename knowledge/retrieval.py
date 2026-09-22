class Retriever:
    def search(self, query, documents):
        query_words = set(query.lower().split())

        scored = []
        for document in documents:
            words = set(document.lower().split())
            score = len(query_words & words)
            scored.append((score, document))

        scored.sort(reverse=True, key=lambda x: x[0])
        return [doc for score, doc in scored if score > 0]

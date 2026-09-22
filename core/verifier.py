class Verifier:
    def verify(self, result):
        if result is None:
            return {"verified": False, "reason": "Résultat vide"}

        if isinstance(result, dict):
            return {
                "verified": result.get("status") in {
                    "completed",
                    "success",
                    "ok",
                },
                "result": result,
            }

        return {
            "verified": True,
            "result": result,
        }

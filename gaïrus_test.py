from gairus_engine import GairusEngine


def main():
    engine = GairusEngine()

    tests = [
        "Développer une application Python",
        "Faire une recherche approfondie sur les agents IA",
        "Analyser un document",
        "Organiser une réunion",
        "Répondre à une question générale",
    ]

    for request in tests:
        result = engine.ask(request)

        print("\n" + "=" * 60)
        print("MISSION :", result["objective"])
        print("AGENT   :", result["route"])
        print("STATUS  :", result["status"])
        print("MODEL   :", result.get("model", "auto"))
        print("VERIFY  :", result["verification"]["verified"])


if __name__ == "__main__":
    main()

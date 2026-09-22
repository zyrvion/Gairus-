from gairus_engine import GairusEngine


def main():
    engine = GairusEngine()

    print("GAÏRUS STATUS")
    print(engine.status())

    print("\nGAÏRUS ROUTING")

    for task in (
        "Développer une application Python",
        "Faire une recherche sur les agents IA",
        "Analyser un document PDF",
        "Préparer une réunion",
        "Répondre à une question générale",
    ):
        result = engine.ask(task)

        print("\n" + "=" * 60)
        print("MISSION :", result["objective"])
        print("AGENT   :", result["route"])
        print("MODEL   :", result["model"])
        print("STATUS  :", result["status"])
        print(
            "LLM     :",
            result["agent_result"]["status"]
        )


if __name__ == "__main__":
    main()

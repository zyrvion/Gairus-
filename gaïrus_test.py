from gairus_engine import GairusEngine


if __name__ == "__main__":
    engine = GairusEngine()

    result = engine.ask(
        "Analyser cette mission et déterminer l'agent approprié"
    )

    print(result)

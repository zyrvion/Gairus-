"""
GAÏRUS CORE — boucle agent minimale mais réelle (Section 21)
    perceive -> plan (modèle) -> act (outil si demandé) -> observe -> répondre
Lancement :  python main.py
"""
import json
import re
import config
import router
import tools
from memory import Memory

SYSTEM_PROMPT = f"""Tu es GAÏRUS, un agent IA personnel.
Tu peux utiliser des outils quand c'est utile. Pour appeler un outil,
réponds UNIQUEMENT avec un bloc JSON de cette forme, rien d'autre :
{{"tool": "<nom_outil>", "params": {{...}}}}

Outils disponibles :
{tools.list_tools_for_model()}

Si tu n'as pas besoin d'outil, réponds normalement en texte libre.
"""

TOOL_CALL_RE = re.compile(r"\{.*\"tool\"\s*:.*\}", re.DOTALL)


def try_parse_tool_call(text: str):
    match = TOOL_CALL_RE.search(text)
    if not match:
        return None
    try:
        obj = json.loads(match.group(0))
        if "tool" in obj:
            return obj
    except json.JSONDecodeError:
        return None
    return None


def check_permission(tool_name: str) -> str:
    return config.TOOL_PERMISSIONS.get(tool_name, "RESTRICTED")


def run_agent_step(mem: Memory, user_input: str) -> str:
    mem.add_message("user", user_input)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += mem.recent_messages(limit=12)

    # PLAN
    raw_response = router.call_model(messages)

    # ACT si le modèle a demandé un outil
    tool_call = try_parse_tool_call(raw_response)
    if tool_call:
        tool_name = tool_call.get("tool")
        params = tool_call.get("params", {})
        permission = check_permission(tool_name)

        if permission == "RESTRICTED":
            result = f"Action refusée (permission RESTRICTED) : {tool_name}"
            mem.log_action(tool_name, json.dumps(params), result, "refused")

        elif permission == "CONFIRM" and config.AUTONOMY_LEVEL != "AUTONOMOUS":
            print(f"\n⚠️  Gaïrus veut exécuter : {tool_name}({params})")
            ok = input("Confirmer ? (o/n) > ").strip().lower()
            if ok == "o":
                result = tools.run_tool(tool_name, params)
                mem.log_action(tool_name, json.dumps(params), result, "ok")
            else:
                result = "Action annulée par l'utilisateur."
                mem.log_action(tool_name, json.dumps(params), result, "refused")
        else:
            result = tools.run_tool(tool_name, params)
            mem.log_action(tool_name, json.dumps(params), result, "ok")

        # OBSERVE + on redemande au modèle de formuler la réponse finale
        follow_up = messages + [
            {"role": "assistant", "content": raw_response},
            {"role": "user", "content": f"[Résultat de l'outil {tool_name}] : {result}\n"
                                         "Formule maintenant une réponse claire pour l'utilisateur."},
        ]
        final_answer = router.call_model(follow_up)
        mem.add_message("assistant", final_answer)
        return final_answer

    mem.add_message("assistant", raw_response)
    return raw_response


def main():
    mem = Memory()
    print("=== GAÏRUS (scaffold Phase 1) ===")
    print(f"Autonomie : {config.AUTONOMY_LEVEL}  |  NO_PAID_PROVIDERS : {config.NO_PAID_PROVIDERS}")
    print("Tape 'exit' pour quitter.\n")

    while True:
        try:
            user_input = input("Toi > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nÀ bientôt, Chief.")
            break
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        answer = run_agent_step(mem, user_input)
        print(f"Gaïrus > {answer}\n")


if __name__ == "__main__":
    main()

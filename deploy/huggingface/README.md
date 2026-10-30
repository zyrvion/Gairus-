---
title: Gaïrus
colorFrom: gray
colorTo: blue
sdk: gradio
sdk_version: 6.30.0
python_version: "3.12"
app_file: app.py
hf_oauth: true
hf_oauth_scopes:
  - write-repos
models:
  - Qwen/Qwen3-4B-Instruct-2507
  - onnx-community/Kokoro-82M-v1.0-ONNX
short_description: "Agent privé : documents, voix FR et présentations vidéo"
---

# Gaïrus

Version cloud personnelle à budget nul : agent borné produisant de vrais
documents Markdown, voix françaises WAV et présentations vidéo MP4.
Conversation IA, plans de mission et mémoire restent disponibles séparément.
L'accès aux données est réservé au propriétaire
du Space connecté avec Hugging Face. Les conversations et mémoires sont
enregistrées dans son dépôt de données privé, pas sur le disque temporaire
du Space et pas dans le navigateur.

## Outils exécutables

L'onglet Agent transforme l'objectif en un plan JSON strictement validé,
exécute uniquement les outils locaux autorisés et vérifie les fichiers
avant de déclarer le travail terminé. Aucun texte du modèle ne peut
ajouter un outil, exécuter une commande arbitraire ou autoriser un paiement.
Les fichiers et leur manifeste SHA-256 sont sauvegardés avec l'état en une
écriture versionnée. Les téléchargements sont fournis dans la réponse privée
authentifiée, jamais dans le cache de fichiers public de Gradio.
Les médias sont stockés comme texte base64 borné dans des fichiers `.b64`
privés, puis décodés et vérifiés avant de restituer les vrais WAV/MP4.

La voix française standard `ff_siwis` utilise
[Kokoro](https://huggingface.co/hexgrad/Kokoro-82M) sur CPU et les
[poids ONNX](https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX)
à la révision `1939ad2a8e416c0acfeecc08a694d14ef25f2231`.
Elle n'appelle pas ElevenLabs et ne clone pas une personne.
Le moteur vidéo assemble une à trois diapositives et la narration avec
FFmpeg. **Ce n'est pas un moteur de scènes animées générées par IA.**
Limites : narration de 1200 caractères, vidéo de 100 secondes au maximum,
6 Mo par fichier et 50 travaux sauvegardés sans effacement automatique.

## Fonctionnement

Le moteur est [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507),
distribué sous licence Apache 2.0. La révision du modèle est fixée dans
`inference.py` et aucun code distant du modèle n'est exécuté.

Le matériel demandé est exclusivement **ZeroGPU gratuit**. Aucun abonnement,
GPU dédié, crédit prépayé ni stockage payant ne doit être activé.
Les comptes personnels gratuits éligibles peuvent héberger deux Spaces
ZeroGPU. Leur quota publié est de cinq minutes de calcul GPU par jour,
avec attente possible : ce n'est pas un service illimité ni une garantie de
disponibilité continue
([documentation ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu)).

## Confidentialité

« Se connecter avec Hugging Face » permet au propriétaire d'autoriser le
stockage dans son dépôt privé. Le jeton OAuth reste côté serveur et n'est
jamais un champ de formulaire, une sortie de l'application ou un message
destiné au modèle. Chaque opération vérifie aussi l'identité réelle du
jeton. Aucun autre compte n'est autorisé à lire ou écrire les données.
Le cookie de connexion ne contient qu'un identifiant opaque signé ;
les informations OAuth restent en mémoire serveur et disparaissent à l'arrêt.
Une reconnexion peut donc être nécessaire après un redémarrage, mais les
conversations et mémoires restent dans le dépôt privé.

Le stockage refuse de fonctionner si le dépôt n'est plus privé. Les mises
à jour vérifient la révision précédente et réessaient en cas de concurrence.
Un échec de sauvegarde n'est jamais présenté comme une sauvegarde réussie.

## Limites de cette version

Les plans générés sont des propositions, pas des actions exécutées.
Aucun message externe, achat, commande arbitraire, changement GitHub ou DNS
n'est exécuté par le modèle. Seul l'encodage FFmpeg à arguments fixes est
autorisé dans l'outil vidéo. La navigation web et les intégrations externes
du runtime complet ne sont pas activées dans cette version gratuite.
Ce n'est pas une copie complète de VIKTOR.
Slack n'est pas connecté : il manque l'application et ses autorisations.
L'API `/service_agent` est privée par clé, sans mémoire ; elle ne constitue
pas à elle seule une intégration Slack.

Le sous-domaine `gairus.zyrvion.io`, la migration des projets VIKTOR et
l'app terrain restent des opérations distinctes. Le site Zyrvion existant
n'est pas modifié par ce déploiement.

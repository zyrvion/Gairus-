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
short_description: Assistant privé, conversations, plans de mission et mémoire
---

# Gaïrus

Version cloud personnelle à budget nul : conversation IA, rédaction, code,
plans de mission et mémoire. L'accès aux données est réservé au propriétaire
du Space connecté avec Hugging Face. Les conversations et mémoires sont
enregistrées dans son dépôt de données privé, pas sur le disque temporaire
du Space et pas dans le navigateur.

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

Le stockage refuse de fonctionner si le dépôt n'est plus privé. Les mises
à jour vérifient la révision précédente et réessaient en cas de concurrence.
Un échec de sauvegarde n'est jamais présenté comme une sauvegarde réussie.

## Limites de cette version

Les plans générés sont des propositions, pas des actions exécutées.
Aucun message externe, achat, commande système, changement GitHub ou DNS
n'est exécuté par le modèle. La navigation web et les intégrations externes
du runtime complet ne sont pas activées dans cette version gratuite.
Ce n'est pas une copie complète de VIKTOR.

Le sous-domaine `gairus.zyrvion.io`, la migration des projets VIKTOR et
l'app terrain restent des opérations distinctes. Le site Zyrvion existant
n'est pas modifié par ce déploiement.

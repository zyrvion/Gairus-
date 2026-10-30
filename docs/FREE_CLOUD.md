# Gaïrus: cloud sans abonnement

Le propriétaire a annulé Render et toute dépense le 25 octobre 2026.
La branche de correction et la pull request nº 2 restent séparées de `main`.
Aucun déploiement de cette branche ne nécessite une fusion dans `main`.

## Hébergement choisi

Le compte Hugging Face existant `NostraEmpire` est vérifié et plus ancien
que trente jours. Il est gratuit, sans capacité de paiement activée.
L'espace `NostraEmpire/gairus` a été créé en demandant exclusivement le matériel
`zero-a10g`, sans disque payant et avec une seule réplique.

Les comptes personnels gratuits éligibles peuvent héberger deux Spaces
ZeroGPU. Le quota publié pour un utilisateur connecté gratuit est de cinq
minutes de GPU par jour ; attente et mise en veille restent possibles
([documentation officielle](https://huggingface.co/docs/hub/spaces-zerogpu)).
Il ne faut jamais présenter cette offre comme illimitée ou garantie 24h/24.
Les Spaces Docker sur CPU ne sont pas une solution gratuite pour ce compte,
car leur création requiert maintenant un abonnement
([règles de création des Spaces](https://huggingface.co/docs/hub/spaces-overview)).

## Source et données

Le contenu publié dans le Space vient seulement de `deploy/huggingface/`.
Ne jamais y copier les bases SQLite historiques, `.env`, journaux, clés,
exports VIKTOR, données de QA ou l'arborescence Git complète.

Les données de cette version sont un document JSON versionné dans le dépôt
de données privé `NostraEmpire/gairus-private-state`, créé séparément.
Elles sont relues depuis ce dépôt après une nouvelle connexion et ne
dépendent pas du disque temporaire du Space.

L'OAuth Hugging Face fournit au serveur le jeton du propriétaire pour ses
opérations dans ce dépôt. Le scope `write-repos` est nécessaire à la sauvegarde ;
le consentement apparaît lors de la première connexion. L'application vérifie
le profil, l'expiration et l'identité réelle du jeton, puis refuse tout dépôt
non privé. Les jetons ne sont ni affichés ni envoyés au modèle
([OAuth Spaces](https://huggingface.co/docs/hub/spaces-oauth),
[OAuth Gradio](https://www.gradio.app/guides/sharing-your-app)).

L'adaptateur remplace la session Gradio par une session serveur : le navigateur
reçoit seulement un identifiant opaque signé, HttpOnly, Secure et SameSite=Lax.
Une nouvelle connexion peut être nécessaire après un redémarrage ; cela ne
supprime pas les données du dépôt privé.

Les écritures utilisent `parent_commit` et réessaient les conflits.
Un dépôt absent, un réseau indisponible ou une sauvegarde échouée ne doit
jamais être remplacé silencieusement par une base vide.

## Fonctions et limites

- Agent borné : objectif, plan JSON validé, exécution d'outils gratuits, preuves
  et fichiers réels. Document Markdown, voix française Kokoro sur CPU et MP4
  de diapositives narrées avec FFmpeg, pas de scènes vidéo générées par IA.
- Travaux et fichiers sauvegardés atomiquement dans le dataset privé ; lecture
  ultérieure vérifie SHA-256, taille et type. Aucun cache public Gradio.
- Conversation réelle avec Qwen3-4B, rédaction, analyse de texte et code.
- Conversations distinctes, mémoire et plans de mission sauvegardés.
- Statuts de suivi explicitement manuels, sans exécution externe implicite.
- API de conversation sans mémoire pour les futures intégrations, protégée
  par une clé de service aléatoire d'au moins quarante caractères.
- API `/service_agent` protégée par la même clé, sans sauvegarde implicite.
  Slack n'est pas raccordé et aucune livraison de fichiers Slack n'est annoncée.
- Pas de navigateur autonome, d'exécution de code, d'envoi externe ou d'achat.
- Le runtime Flask complet reste disponible dans le dépôt, mais n'est pas
  prétendu intégralement activé dans ce mode gratuit.

La parité avec VIKTOR n'est pas atteinte par ce premier mode gratuit.
Les exports personnels VIKTOR et l'app terrain restent à migrer séparément.
Le DNS de `zyrvion.io` n'est pas modifié sans accès Spaceship ; aucune autre
application Zyrvion n'est écrasée.

## Contrôles avant annonce de disponibilité

1. Refus de tout matériel autre que `zero-a10g` et absence de stockage payant.
2. Dataset privé et sauvegarde concurrente testés avec des données synthétiques.
3. Connexion et contrôles d'accès, conversation, mémoire, missions, rechargement.
4. Contrôles navigateur ordinateur et largeur 375 px.
5. Réponse réelle du modèle sur le Space publié.
6. Aucune donnée synthétique de QA laissée comme donnée de l'utilisateur.
7. État de la migration, du DNS et des limitations annoncé sans exagération.

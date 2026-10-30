# Gaïrus : application propre et installation stable

État vérifié le 30 octobre 2026. Cette préparation n'est pas une mise en
production ni un raccordement d'API.

## Exigences du propriétaire

- Une vraie application à `https://gairus.zyrvion.io`, pas une redirection vers
  Hugging Face ni une nouvelle façade qui y conserve discrètement le moteur.
- Donner des missions depuis le web et depuis une application Slack Gaïrus.
- Ajouter l'application à l'écran d'accueil et conserver son identité et son
  adresse lors des mises à jour.
- Aucun paiement, abonnement, dépassement payant ou secours IA payant.
- Garder Zyrvion et ses données inchangés. Ne pas fusionner dans `main`.

## Préparation réalisée dans la branche de correction

Le frontend Flask existant est conservé. Le manifeste a une identité et une
portée stables `/`, des icônes PNG 180/192/512 réellement présentes et le mode
standalone. Les icônes réutilisent le G typographique existant.

Le service worker est maintenant enregistré à `/sw.js`, avec vérification sans
cache HTTP. Une version en attente propose « Actualiser Gaïrus » et ne recharge
jamais automatiquement une saisie. L'activation demandée recharge la même
adresse, pas un autre lien d'installation.

Le cache contient uniquement une page hors connexion, son CSS et trois icônes.
Ni page authentifiée, clé, mémoire, mission, réponse API, document, voix ou
vidéo privée n'est mis en cache. Aucune tâche hors connexion n'est envoyée ou
rejouée automatiquement.

Le rafraîchissement des données conserve désormais le titre, l'objectif, la
note ou le texte en cours de saisie dans la même vue, avec la position du
curseur. Un formulaire n'est vidé qu'après une sauvegarde réussie.

## Contrôles réellement effectués

- Suite Python : 122 tests réussis sous Python 3.14.8, dont sept nouveaux
  contrôles PWA, sur des bases et journaux de test isolés.
- Navigateur : connexion, rejet d'une mauvaise clé, toutes les vues, création
  d'une mission avec son titre, note conservée après réouverture, réponse
  explicite en l'absence de fournisseur IA et déconnexion.
- Bureau et mobile 375 × 812 : largeur de document de 375 px, application
  contenue dans la hauteur disponible, contrôle du menu, pas de nouvelle
  erreur JavaScript.
- Rafraîchissement automatique réel : texte et curseur conservés.
- Cycle de mise à jour réel : deux scripts de worker servis successivement
  par un serveur QA isolé ; nouvelle version en attente, brouillon intact
  avant validation, clic sur « Actualiser Gaïrus », même URL et worker activé.
- Coupure réseau réelle dans le navigateur : page publique hors connexion,
  cache limité aux cinq ressources prévues, puis reconnexion.
- Le manifeste est accepté par Chromium. L'installation effective sur le
  téléphone du propriétaire n'a pas été validée ; le contexte automatisé
  privé signale `in-incognito`, ce n'est pas une preuve d'installation.

Le serveur `scripts/qa_pwa_server.py` est exclusivement un banc d'essai et ne
doit pas être un point d'entrée de production. Son changement de version
requiert la clé API de test ; il ne simule aucune réussite de fournisseur.

## Déploiement et intégrations encore bloqués

La commande officielle de connexion Vercel n'a pas reçu d'autorisation
exploitable après la confirmation du propriétaire ; elle a terminé avec le
code 1 et `whoami` indique encore une déconnexion. Aucun compte, projet,
stockage, abonnement ni déploiement Vercel n'a été créé.

Le site actuel reste le précédent accès vers Hugging Face. Ni son DNS ni son
hébergement n'ont été basculés durant cette préparation. Les conversations et
fichiers privés historiques ne sont pas migrés ou effacés.

Le runtime existant utilise SQLite et un ordonnanceur dans un processus
permanent. Il ne doit pas être publié tel quel dans des fonctions éphémères
en prétendant assurer la persistance ou une exécution continue. Une solution
de stockage durable et une exécution de missions adaptée sont des prérequis.

Slack n'est pas connecté. Aucun jeton Gaïrus distinct n'est disponible et les
jetons ZAREL ou ORTA ne sont pas réutilisés. Aucune nouvelle API IA, voix ou
vidéo n'a été activée. Une configuration présente n'est pas une connexion
testée.

La tentative de coordination autorisée avec la tâche ZAREL a reçu un refus
d'accès ; aucun message n'a été transmis. Ses calculs sont restés intacts.

Vercel Hobby est limité à un usage personnel non commercial. Ce n'est donc
pas une base commerciale gratuite à annoncer pour la cible future
([conditions Vercel](https://vercel.com/docs/limits/fair-use-guidelines)).
L'offre et les droits du compte réel doivent être vérifiés avant de choisir
l'architecture ; aucune conversion payante n'est autorisée.

## Conditions avant d'annoncer « utilisable »

- Accès d'hébergement réellement vérifié et offre compatible avec le budget.
- Stockage privé durable et restauration des données vérifiée.
- Authentification propriétaire adaptée à la version publiée.
- Un vrai aller-retour de mission web, résultat et fichier contrôlés.
- Une application Slack distincte avec une vraie réponse au propriétaire.
- Fournisseurs explicitement configurés et testés dans leurs quotas gratuits ;
  ne pas confondre une vidéo de diapositives avec un film génératif.
- HTTPS et installation à la même adresse vérifiés après le basculement.

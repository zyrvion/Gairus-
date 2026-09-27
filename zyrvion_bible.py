#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ZYRVION BIBLE
Universal Knowledge Core
Agent: Gaïrus

Objectif:
- architecture universelle de services
- catalogue extensible
- objectif de plus de 1 000 000 000 services
- recherche et orchestration des services
- enrichissement dynamique
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import re


ZYRVION_NAME = "ZYRVION"
ZYRVION_VERSION = "1.0.0"
CATALOGUE_TARGET = 1_000_000_000


ARCHITECTURE = [
    "Univers",
    "Secteur",
    "Catégorie",
    "Sous-catégorie",
    "Service",
    "Variante",
    "Localisation",
    "Prestataire",
    "Disponibilité",
    "Prix",
    "Conditions",
    "Exécution",
    "Vérification",
    "Évaluation",
    "Amélioration",
]


PRINCIPLES = [
    "Toute demande peut devenir un objectif.",
    "Tout objectif peut être décomposé en tâches.",
    "Toute tâche peut nécessiter plusieurs compétences.",
    "Toute compétence peut être associée à plusieurs services.",
    "Chaque service peut avoir plusieurs variantes.",
    "Le contexte influence le service choisi.",
    "La localisation influence les possibilités.",
    "Le budget influence les possibilités.",
    "L'urgence influence les possibilités.",
    "Plusieurs services peuvent être combinés.",
    "Les résultats doivent être vérifiés.",
    "Les erreurs doivent être détectées.",
    "Les erreurs doivent être corrigées lorsque possible.",
    "Le catalogue doit pouvoir évoluer.",
    "Les doublons doivent être évités.",
]


UNIVERS = {
    1: "Besoins essentiels du quotidien",
    2: "Commerce, produits et distribution",
    3: "Services professionnels et expertises",
    4: "Santé, médecine, beauté et bien-être",
    5: "Éducation, formation et connaissance",
    6: "Transport, mobilité et logistique",
    7: "Habitat, immobilier, construction et environnement",
    8: "Finance, banque, assurance et économie",
    9: "Technologie, informatique, intelligence artificielle et innovation",
    10: "Tourisme, voyage, hôtellerie et expériences",
    11: "Agriculture, élevage, alimentation et ressources naturelles",
    12: "Commerce, entreprises, vente et distribution mondiale",
    13: "Industrie, production, artisanat et fabrication",
}


@dataclass
class Service:
    id: int
    nom: str
    univers: str
    secteur: str = ""
    categorie: str = ""
    sous_categorie: str = ""
    variantes: List[str] = field(default_factory=list)
    localisations: List[str] = field(default_factory=list)
    prestataires: List[str] = field(default_factory=list)
    description: str = ""
    actif: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


SERVICES: Dict[int, Service] = {}


def ajouter_service(
    service_id: int,
    nom: str,
    univers: str,
    secteur: str = "",
    categorie: str = "",
    sous_categorie: str = "",
    variantes: Optional[List[str]] = None,
    localisations: Optional[List[str]] = None,
    prestataires: Optional[List[str]] = None,
    description: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Service:

    if service_id in SERVICES:
        return SERVICES[service_id]

    service = Service(
        id=service_id,
        nom=nom,
        univers=univers,
        secteur=secteur,
        categorie=categorie,
        sous_categorie=sous_categorie,
        variantes=variantes or [],
        localisations=localisations or [],
        prestataires=prestataires or [],
        description=description,
        metadata=metadata or {},
    )

    SERVICES[service_id] = service
    return service


def generer_variantes() -> List[str]:
    return [
        "standard",
        "premium",
        "express",
        "à domicile",
        "en ligne",
        "professionnel",
        "personnalisé",
        "automatisé",
        "local",
        "international",
    ]


def enrichir_service(service: Service) -> None:

    if not service.variantes:
        service.variantes = generer_variantes()

    if not service.localisations:
        service.localisations = [
            "local",
            "national",
            "international",
        ]

# ============================================================
# SERVICES DE BASE
# ============================================================

BASE_SERVICES = [

    # UNIVERS 1
    (1, "Courses alimentaires", "Besoins essentiels du quotidien"),
    (2, "Livraison de repas", "Besoins essentiels du quotidien"),
    (3, "Nettoyage domestique", "Besoins essentiels du quotidien"),
    (4, "Blanchisserie", "Besoins essentiels du quotidien"),
    (5, "Coiffure à domicile", "Besoins essentiels du quotidien"),
    (6, "Réparation domestique", "Besoins essentiels du quotidien"),
    (7, "Plomberie", "Besoins essentiels du quotidien"),
    (8, "Électricité domestique", "Besoins essentiels du quotidien"),
    (9, "Garde d'enfants", "Besoins essentiels du quotidien"),
    (10, "Aide à domicile", "Besoins essentiels du quotidien"),

    # UNIVERS 2
    (81, "Boutique en ligne", "Commerce, produits et distribution"),
    (82, "Marketplace", "Commerce, produits et distribution"),
    (83, "Livraison de produits", "Commerce, produits et distribution"),
    (84, "Achat de vêtements", "Commerce, produits et distribution"),
    (85, "Achat d'électronique", "Commerce, produits et distribution"),
    (86, "Achat de meubles", "Commerce, produits et distribution"),
    (87, "Achat de produits alimentaires", "Commerce, produits et distribution"),
    (88, "Achat de fournitures", "Commerce, produits et distribution"),
    (89, "Comparateur de produits", "Commerce, produits et distribution"),
    (90, "Service après-vente", "Commerce, produits et distribution"),

    # UNIVERS 3
    (201, "Conseil juridique", "Services professionnels et expertises"),
    (202, "Comptabilité", "Services professionnels et expertises"),
    (203, "Audit", "Services professionnels et expertises"),
    (204, "Conseil financier", "Services professionnels et expertises"),
    (205, "Conseil marketing", "Services professionnels et expertises"),
    (206, "Création graphique", "Services professionnels et expertises"),
    (207, "Traduction", "Services professionnels et expertises"),
    (208, "Interprétation", "Services professionnels et expertises"),
    (209, "Conseil en entreprise", "Services professionnels et expertises"),
    (210, "Recrutement", "Services professionnels et expertises"),

    # UNIVERS 4
    (341, "Médecin généraliste", "Santé, médecine, beauté et bien-être"),
    (342, "Consultation médicale à domicile", "Santé, médecine, beauté et bien-être"),
    (343, "Dentiste", "Santé, médecine, beauté et bien-être"),
    (344, "Pharmacie", "Santé, médecine, beauté et bien-être"),
    (345, "Laboratoire médical", "Santé, médecine, beauté et bien-être"),
    (346, "Kinésithérapie", "Santé, médecine, beauté et bien-être"),
    (347, "Psychologie", "Santé, médecine, beauté et bien-être"),
    (348, "Nutrition", "Santé, médecine, beauté et bien-être"),
    (349, "Opticien", "Santé, médecine, beauté et bien-être"),
    (350, "Beauté et esthétique", "Santé, médecine, beauté et bien-être"),

    # UNIVERS 5
    (471, "École maternelle", "Éducation, formation et connaissance"),
    (472, "École primaire", "Éducation, formation et connaissance"),
    (473, "Collège", "Éducation, formation et connaissance"),
    (474, "Lycée", "Éducation, formation et connaissance"),
    (475, "Université", "Éducation, formation et connaissance"),
    (476, "Formation professionnelle", "Éducation, formation et connaissance"),
    (477, "Cours particuliers", "Éducation, formation et connaissance"),
    (478, "Formation en ligne", "Éducation, formation et connaissance"),
    (479, "Bibliothèque numérique", "Éducation, formation et connaissance"),
    (480, "Développement des compétences", "Éducation, formation et connaissance"),

    # UNIVERS 6
    (601, "Taxi traditionnel", "Transport, mobilité et logistique"),
    (602, "VTC", "Transport, mobilité et logistique"),
    (603, "Location de voiture", "Transport, mobilité et logistique"),
    (604, "Location de moto", "Transport, mobilité et logistique"),
    (605, "Transport public", "Transport, mobilité et logistique"),
    (606, "Transport de marchandises", "Transport, mobilité et logistique"),
    (607, "Livraison express", "Transport, mobilité et logistique"),
    (608, "Déménagement", "Transport, mobilité et logistique"),
    (609, "Fret international", "Transport, mobilité et logistique"),
    (610, "Logistique intelligente", "Transport, mobilité et logistique"),

    # UNIVERS 7
    (731, "Agence immobilière", "Habitat, immobilier, construction et environnement"),
    (732, "Location immobilière", "Habitat, immobilier, construction et environnement"),
    (733, "Vente immobilière", "Habitat, immobilier, construction et environnement"),
    (734, "Construction de maison", "Habitat, immobilier, construction et environnement"),
    (735, "Rénovation", "Habitat, immobilier, construction et environnement"),
    (736, "Architecture", "Habitat, immobilier, construction et environnement"),
    (737, "Décoration intérieure", "Habitat, immobilier, construction et environnement"),
    (738, "Jardinage", "Habitat, immobilier, construction et environnement"),
    (739, "Gestion des déchets", "Habitat, immobilier, construction et environnement"),
    (740, "Maison connectée", "Habitat, immobilier, construction et environnement"),

]

# ============================================================
# SERVICES DE BASE : UNIVERS 8 À 13
# ============================================================

BASE_SERVICES += [

    # UNIVERS 8
    (871, "Compte bancaire personnel", "Finance, banque, assurance et économie"),
    (872, "Compte professionnel", "Finance, banque, assurance et économie"),
    (873, "Transfert d'argent", "Finance, banque, assurance et économie"),
    (874, "Paiement numérique", "Finance, banque, assurance et économie"),
    (875, "Assurance automobile", "Finance, banque, assurance et économie"),
    (876, "Assurance habitation", "Finance, banque, assurance et économie"),
    (877, "Assurance santé", "Finance, banque, assurance et économie"),
    (878, "Crédit", "Finance, banque, assurance et économie"),
    (879, "Épargne", "Finance, banque, assurance et économie"),
    (880, "Investissement", "Finance, banque, assurance et économie"),

    # UNIVERS 9
    (1001, "Dépannage informatique", "Technologie, informatique, intelligence artificielle et innovation"),
    (1002, "Développement logiciel", "Technologie, informatique, intelligence artificielle et innovation"),
    (1003, "Développement web", "Technologie, informatique, intelligence artificielle et innovation"),
    (1004, "Développement mobile", "Technologie, informatique, intelligence artificielle et innovation"),
    (1005, "Cybersécurité", "Technologie, informatique, intelligence artificielle et innovation"),
    (1006, "Cloud computing", "Technologie, informatique, intelligence artificielle et innovation"),
    (1007, "Intelligence artificielle", "Technologie, informatique, intelligence artificielle et innovation"),
    (1008, "Automatisation", "Technologie, informatique, intelligence artificielle et innovation"),
    (1009, "Analyse de données", "Technologie, informatique, intelligence artificielle et innovation"),
    (1010, "Robotique", "Technologie, informatique, intelligence artificielle et innovation"),

    # UNIVERS 10
    (1131, "Hôtel économique", "Tourisme, voyage, hôtellerie et expériences"),
    (1132, "Hôtel", "Tourisme, voyage, hôtellerie et expériences"),
    (1133, "Hôtel de luxe", "Tourisme, voyage, hôtellerie et expériences"),
    (1134, "Location de logement", "Tourisme, voyage, hôtellerie et expériences"),
    (1135, "Billet d'avion", "Tourisme, voyage, hôtellerie et expériences"),
    (1136, "Billet de train", "Tourisme, voyage, hôtellerie et expériences"),
    (1137, "Guide touristique", "Tourisme, voyage, hôtellerie et expériences"),
    (1138, "Excursion", "Tourisme, voyage, hôtellerie et expériences"),
    (1139, "Réservation de voyage", "Tourisme, voyage, hôtellerie et expériences"),
    (1140, "Organisation de voyage", "Tourisme, voyage, hôtellerie et expériences"),

    # UNIVERS 11
    (1261, "Agriculture traditionnelle", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1262, "Agriculture moderne", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1263, "Agriculture biologique", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1264, "Élevage bovin", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1265, "Élevage avicole", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1266, "Pêche", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1267, "Irrigation", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1268, "Vente de produits agricoles", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1269, "Transformation alimentaire", "Agriculture, élevage, alimentation et ressources naturelles"),
    (1270, "Gestion des ressources naturelles", "Agriculture, élevage, alimentation et ressources naturelles"),

    # UNIVERS 12
    (1381, "Boutique alimentaire", "Commerce, entreprises, vente et distribution mondiale"),
    (1382, "Supermarché", "Commerce, entreprises, vente et distribution mondiale"),
    (1383, "Grossiste", "Commerce, entreprises, vente et distribution mondiale"),
    (1384, "Import-export", "Commerce, entreprises, vente et distribution mondiale"),
    (1385, "Distribution", "Commerce, entreprises, vente et distribution mondiale"),
    (1386, "Vente B2B", "Commerce, entreprises, vente et distribution mondiale"),
    (1387, "Vente B2C", "Commerce, entreprises, vente et distribution mondiale"),
    (1388, "E-commerce mondial", "Commerce, entreprises, vente et distribution mondiale"),
    (1389, "Marketplace mondiale", "Commerce, entreprises, vente et distribution mondiale"),
    (1390, "Commerce universel Zyrvion", "Commerce, entreprises, vente et distribution mondiale"),

    # UNIVERS 13
    (1501, "Usine", "Industrie, production, artisanat et fabrication"),
    (1502, "Production industrielle", "Industrie, production, artisanat et fabrication"),
    (1503, "Fabrication", "Industrie, production, artisanat et fabrication"),
    (1504, "Artisanat", "Industrie, production, artisanat et fabrication"),
    (1505, "Matières premières", "Industrie, production, artisanat et fabrication"),
    (1506, "Maintenance industrielle", "Industrie, production, artisanat et fabrication"),
    (1507, "Ingénierie industrielle", "Industrie, production, artisanat et fabrication"),
    (1508, "Chaîne de production", "Industrie, production, artisanat et fabrication"),
    (1509, "Automatisation industrielle", "Industrie, production, artisanat et fabrication"),
    (1510, "Contrôle qualité", "Industrie, production, artisanat et fabrication"),

]

# ============================================================
# ENREGISTREMENT DES SERVICES
# ============================================================

def charger_services() -> None:
    for service_id, nom, univers in BASE_SERVICES:
        ajouter_service(
            service_id=service_id,
            nom=nom,
            univers=univers,
            description=f"Service universel ZYRVION : {nom}",
        )

    for service in SERVICES.values():
        enrichir_service(service)


# ============================================================
# RECHERCHE INTELLIGENTE
# ============================================================

def rechercher_service(
    requete: str,
    univers: Optional[str] = None,
) -> List[Service]:

    mots = [
        mot.lower()
        for mot in re.findall(r"\w+", requete, flags=re.UNICODE)
        if len(mot) > 1
    ]

    resultats = []

    for service in SERVICES.values():

        if univers:
            if service.univers.lower() != univers.lower():
                continue

        texte = " ".join([
            service.nom,
            service.univers,
            service.secteur,
            service.categorie,
            service.sous_categorie,
            service.description,
            " ".join(service.variantes),
        ]).lower()

        score = 0

        for mot in mots:
            if mot in texte:
                score += 1

        if score:
            resultats.append((score, service))

    resultats.sort(
        key=lambda element: (
            -element[0],
            element[1].id,
        )
    )

    return [
        service
        for _, service in resultats
    ]


# ============================================================
# ACCÈS AU CATALOGUE
# ============================================================

def get_service(service_id: int) -> Optional[Service]:
    return SERVICES.get(service_id)


def get_all_services() -> List[Service]:
    return list(SERVICES.values())


def get_catalogue() -> Dict[int, Dict[str, Any]]:
    return {
        service_id: service.to_dict()
        for service_id, service in SERVICES.items()
    }


# ============================================================
# CRÉATION DYNAMIQUE
# ============================================================

def creer_service_automatiquement(
    nom: str,
    univers: str,
    description: str = "",
) -> Service:

    nouveau_id = (
        max(SERVICES.keys()) + 1
        if SERVICES
        else 1
    )

    return ajouter_service(
        service_id=nouveau_id,
        nom=nom,
        univers=univers,
        description=description,
    )


# ============================================================
# EXPORT DU CATALOGUE
# ============================================================

def exporter_catalogue(
    chemin: str = "zyrvion_catalogue.json",
) -> Path:

    chemin_fichier = Path(chemin)

    contenu = {
        "nom": ZYRVION_NAME,
        "version": ZYRVION_VERSION,
        "objectif_services": CATALOGUE_TARGET,
        "nombre_services": len(SERVICES),
        "univers": UNIVERS,
        "architecture": ARCHITECTURE,
        "services": get_catalogue(),
    }

    chemin_fichier.write_text(
        json.dumps(
            contenu,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return chemin_fichier


# ============================================================
# CONTEXTE DU CERVEAU ZYRVION
# ============================================================

SYSTEM_CONTEXT = """
ZYRVION est une architecture universelle d'intelligence,
d'orchestration et de services.

Le système doit :

- comprendre une demande humaine ;
- identifier le besoin réel ;
- transformer le besoin en objectif ;
- décomposer l'objectif ;
- identifier les tâches ;
- identifier les compétences nécessaires ;
- rechercher les services correspondants ;
- rechercher les variantes ;
- prendre en compte la localisation ;
- prendre en compte le budget ;
- prendre en compte l'urgence ;
- prendre en compte les contraintes ;
- combiner plusieurs services ;
- construire une solution ;
- exécuter les étapes lorsque les outils nécessaires sont disponibles ;
- vérifier les résultats ;
- détecter les erreurs ;
- corriger les erreurs lorsque possible ;
- conserver les informations utiles ;
- enrichir le catalogue.

ZYRVION doit être extensible.

L'objectif architectural est de pouvoir représenter
plus de 1 000 000 000 de services, variantes,
compétences, prestataires, localisations et combinaisons.
"""


# ============================================================
# BIBLE ZYRVION
# ============================================================

BIBLE_ZYRVION = {
    "nom": ZYRVION_NAME,
    "version": ZYRVION_VERSION,
    "objectif": CATALOGUE_TARGET,
    "architecture": ARCHITECTURE,
    "principes": PRINCIPLES,
    "univers": UNIVERS,
    "vision_milliard_services": True,
    "catalogue_universel": True,
    "structure_historique": {
        "tome": "Tome VII",
        "livres": [
            "Livre XCI",
            "Livre XCII",
            "Livre XCIII",
        ],
    },
    "system_context": SYSTEM_CONTEXT,
}


# ============================================================
# CONTEXTE COMPLET POUR GAÏRUS
# ============================================================

def get_brain_context() -> Dict[str, Any]:

    return {
        "agent": "Gaïrus",
        "system": ZYRVION_NAME,
        "version": ZYRVION_VERSION,
        "bible": BIBLE_ZYRVION,
        "catalogue": get_catalogue(),
    }


# ============================================================
# DIAGNOSTIC
# ============================================================

def diagnostic() -> Dict[str, Any]:

    return {
        "agent": "Gaïrus",
        "zyrvion": ZYRVION_NAME,
        "version": ZYRVION_VERSION,
        "status": "ok",
        "univers": len(UNIVERS),
        "services": len(SERVICES),
        "objectif": CATALOGUE_TARGET,
        "architecture_niveaux": len(ARCHITECTURE),
    }


# ============================================================
# INITIALISATION
# ============================================================

charger_services()


# ============================================================
# EXÉCUTION DIRECTE
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("ZYRVION BIBLE")
    print("=" * 60)

    infos = diagnostic()

    print(f"Agent                : {infos['agent']}")
    print(f"Système              : {infos['zyrvion']}")
    print(f"Version              : {infos['version']}")
    print(f"Univers              : {infos['univers']}")
    print(f"Services             : {infos['services']}")
    print(
        f"Objectif             : "
        f"{infos['objectif']:,}".replace(",", " ")
    )
    print(
        f"Architecture         : "
        f"{infos['architecture_niveaux']} niveaux"
    )
    print("Catalogue universel  : ACTIF")
    print("Vision milliard      : ACTIF")
    print("Statut               : OK")

    fichier = exporter_catalogue()

    print(f"Export               : {fichier}")
    print("=" * 60)

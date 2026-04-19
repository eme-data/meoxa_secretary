"""Générateur de DPA (Data Processing Agreement / Contrat de sous-traitance RGPD).

Le rendu est du HTML imprimable (CSS @media print). Le client télécharge la page
et peut utiliser Ctrl+P → "Enregistrer au format PDF" dans son navigateur.

⚠️ Ce template fournit une base conforme aux articles 28 et 32 RGPD, mais n'est
pas un avis juridique. À faire valider par un avocat avant signature pour des
contrats à fort enjeu.
"""

from __future__ import annotations

from datetime import UTC, datetime

from meoxa_secretary.models.tenant import Tenant


def render_dpa_html(
    *,
    tenant: Tenant,
    legal_name: str,
    address: str,
    signatory_name: str,
    signatory_title: str,
    dpo_email: str | None = None,
    effective_date: datetime | None = None,
) -> str:
    """Rend le DPA en HTML avec CSS d'impression intégré."""
    effective_date = effective_date or datetime.now(UTC)
    date_str = effective_date.strftime("%d %B %Y")

    # Liste des sous-traitants ultérieurs — à ajuster si la stack évolue.
    subprocessors = [
        ("Anthropic PBC", "États-Unis", "LLM Claude (rédaction & synthèse)", "DPA Anthropic + clauses contractuelles types"),
        ("Microsoft Ireland", "Irlande", "Graph API (emails, calendrier, Teams, OneDrive)", "Signé dans le contrat M365 du client"),
        ("Stripe Payments Europe Ltd", "Irlande", "Facturation & paiement", "DPA Stripe"),
        ("Voyage AI, Inc.", "États-Unis", "Embeddings (mémoire contextuelle)", "DPA Voyage AI + CCT"),
        ("OVH SAS / hébergeur VPS", "France/UE", "Hébergement du serveur applicatif", "DPA de l'hébergeur"),
    ]

    subproc_rows = "\n".join(
        f"<tr><td>{name}</td><td>{country}</td><td>{purpose}</td><td>{contract}</td></tr>"
        for name, country, purpose, contract in subprocessors
    )

    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>DPA — {tenant.name} / Meoxa</title>
<style>
  @page {{ size: A4; margin: 20mm; }}
  body {{ font-family: Georgia, serif; color: #111; line-height: 1.5; max-width: 760px; margin: 2em auto; padding: 0 1em; }}
  h1 {{ font-size: 22pt; border-bottom: 2px solid #0ea5e9; padding-bottom: 4pt; }}
  h2 {{ font-size: 14pt; margin-top: 1.8em; color: #0369a1; }}
  h3 {{ font-size: 11pt; }}
  table {{ width: 100%; border-collapse: collapse; margin: 0.5em 0; font-size: 9.5pt; }}
  th, td {{ border: 1px solid #999; padding: 6px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #f3f4f6; }}
  .meta {{ background: #f3f4f6; padding: 8px 12px; border-radius: 6px; font-size: 10pt; }}
  .signatures {{ display: flex; gap: 2em; margin-top: 3em; page-break-inside: avoid; }}
  .signatures > div {{ flex: 1; border-top: 1px solid #333; padding-top: 4pt; font-size: 10pt; }}
  .small {{ font-size: 9pt; color: #555; }}
  @media print {{
    body {{ margin: 0; }}
    .no-print {{ display: none; }}
  }}
  .no-print {{ position: fixed; top: 12px; right: 12px; background: #0ea5e9; color: white;
               padding: 6px 12px; border-radius: 6px; text-decoration: none; font-family: sans-serif; }}
</style>
</head>
<body>

<a class="no-print" href="javascript:window.print()">Imprimer / PDF</a>

<h1>Contrat de sous-traitance de données personnelles (DPA)</h1>
<p class="small">En application de l'article 28 du Règlement (UE) 2016/679 (RGPD)</p>

<div class="meta">
  <strong>Date d'effet :</strong> {date_str}<br>
  <strong>Responsable du traitement (Client) :</strong> {legal_name}<br>
  <strong>Adresse :</strong> {address}<br>
  <strong>Sous-traitant :</strong> Meoxa — {tenant.name if tenant else ''} (le « Prestataire »)<br>
  <strong>Contact DPO Prestataire :</strong> dpo@meoxa.app<br>
  {f'<strong>DPO / contact Client :</strong> {dpo_email}<br>' if dpo_email else ''}
</div>

<h2>1. Objet</h2>
<p>Le présent contrat définit les conditions dans lesquelles le Prestataire traite des
données à caractère personnel pour le compte du Client dans le cadre du service
« Pack Secrétariat » (automatisation des emails, génération de comptes-rendus de réunions,
gestion d'agenda), accessible sur <em>secretary.meoxa.app</em>.</p>

<h2>2. Description du traitement</h2>
<table>
  <tr><th>Nature & finalité</th>
  <td>Automatisation des tâches de secrétariat : rédaction de brouillons d'emails,
  génération de comptes-rendus de réunions à partir d'enregistrements Teams,
  indexation d'un contexte interne pour pertinence des réponses, suggestions d'agenda.</td></tr>
  <tr><th>Catégories de données</th>
  <td>Identifiants professionnels (nom, email), contenu des emails professionnels,
  enregistrements audio/vidéo de réunions Teams, transcriptions, métadonnées d'agenda,
  données techniques (logs, adresses IP).</td></tr>
  <tr><th>Catégories de personnes</th>
  <td>Employés et interlocuteurs professionnels du Client.</td></tr>
  <tr><th>Durée</th>
  <td>Durée de l'abonnement. Les données sont supprimées dans un délai de 30 jours
  maximum après résiliation (hors obligations légales de conservation).</td></tr>
</table>

<h2>3. Obligations du Prestataire</h2>
<p>Le Prestataire s'engage à :</p>
<ul>
  <li>Ne traiter les données que sur instruction documentée du Client (usage du service).</li>
  <li>Garantir la confidentialité par toute personne habilitée.</li>
  <li>Mettre en œuvre les mesures techniques et organisationnelles appropriées (cf. §7).</li>
  <li>Notifier le Client sans délai en cas de violation de données personnelles.</li>
  <li>Assister le Client dans la réponse aux demandes d'exercice des droits des personnes.</li>
  <li>Au choix du Client, supprimer ou restituer les données au terme du contrat.</li>
</ul>

<h2>4. Sous-traitants ultérieurs</h2>
<p>Le Client autorise le recours aux sous-traitants listés ci-dessous. Toute modification
de cette liste fera l'objet d'une notification préalable au Client, qui pourra s'y opposer
pour motifs légitimes.</p>
<table>
  <tr><th>Sous-traitant</th><th>Pays</th><th>Finalité</th><th>Encadrement</th></tr>
  {subproc_rows}
</table>

<h2>5. Transferts hors UE</h2>
<p>Certains sous-traitants sont situés aux États-Unis. Les transferts sont encadrés par
les Clauses Contractuelles Types de la Commission européenne (décision 2021/914) et par
les engagements DPA spécifiques de chaque sous-traitant.</p>

<h2>6. Droits des personnes concernées</h2>
<p>Le Prestataire met à disposition du Client les fonctions techniques nécessaires à
l'exercice des droits d'accès, rectification, effacement, portabilité et opposition via
l'interface d'administration ({'https://' + (tenant.slug if tenant else '') + '.app'} → Organisation → RGPD).</p>

<h2>7. Sécurité</h2>
<ul>
  <li>Isolation multi-tenant au niveau base de données (Row-Level Security PostgreSQL).</li>
  <li>Chiffrement des secrets applicatifs au repos (Fernet AES-128-CBC + HMAC).</li>
  <li>Chiffrement en transit (TLS 1.2+, Let's Encrypt) sur toutes les communications externes.</li>
  <li>Authentification avec mot de passe fort + 2FA TOTP disponible.</li>
  <li>Journal d'audit immuable des accès administratifs et des connexions.</li>
  <li>Sauvegardes chiffrées quotidiennes, rétention 14 jours, copie hors site.</li>
  <li>Tests de restauration mensuels.</li>
</ul>

<h2>8. Rétention & suppression</h2>
<p>Le Client peut configurer une politique de rétention automatique des transcriptions
(onglet « Paramètres org. » → <em>retention.transcripts_days</em>). En cas d'inaction,
aucune suppression automatique n'est appliquée au-delà du terme du contrat.</p>

<h2>9. Notification de violation</h2>
<p>En cas de violation de données affectant les données du Client, le Prestataire notifie
le Client dans les 72 heures suivant la prise de connaissance, avec : nature de la violation,
catégories et volumes concernés, conséquences probables, mesures prises.</p>

<h2>10. Audit</h2>
<p>Le Prestataire met à disposition du Client les documents relatifs aux mesures de sécurité
et, sous préavis raisonnable (30 jours), autorise un audit sur site ou distant.</p>

<h2>11. Responsabilité & réversibilité</h2>
<p>Au terme du contrat, le Client peut à tout moment exporter ses données via l'interface
(« Organisation → Exporter mes données »). Après un délai de 30 jours, les données sont
définitivement supprimées de toutes les bases et sauvegardes accessibles.</p>

<div class="signatures">
  <div>
    <strong>Pour le Client</strong><br>
    {signatory_name}<br>
    {signatory_title}<br>
    Fait le __________________<br>
    Signature :
  </div>
  <div>
    <strong>Pour le Prestataire — Meoxa</strong><br>
    Mathieu d'Oliveira<br>
    Fondateur<br>
    Fait le {date_str}<br>
    Signature :
  </div>
</div>

<p class="small" style="margin-top: 3em;">
Document généré automatiquement le {effective_date.strftime('%d/%m/%Y %H:%M UTC')} — version 1.0.
À relire par un conseil juridique avant signature pour tout enjeu critique.
</p>

</body>
</html>
"""

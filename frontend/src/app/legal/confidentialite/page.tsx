import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Politique de confidentialité — Secretary by Meoxa",
  description:
    "Politique de confidentialité et traitement des données personnelles de Secretary, conforme RGPD.",
};

export default function ConfidentialitePage() {
  return (
    <>
      <h1>Politique de confidentialité</h1>
      <p className="text-sm text-slate-400">
        Dernière mise à jour : avril 2026 · Conforme au Règlement (UE) 2016/679 (RGPD)
      </p>

      <h2>1. Responsable du traitement</h2>
      <p>
        Le responsable du traitement des données personnelles collectées via Secretary
        est <strong>Meoxa</strong>, {"{{FORME_JURIDIQUE}}"} immatriculée au RCS de{" "}
        {"{{VILLE_RCS}}"} sous le numéro {"{{SIREN}}"}, dont le siège social est situé{" "}
        {"{{ADRESSE_SIEGE}}"}.
      </p>
      <p>
        Délégué à la protection des données (DPO) :{" "}
        <a href="mailto:dpo@meoxa.app">dpo@meoxa.app</a>.
      </p>

      <h2>2. Nature du service</h2>
      <p>
        <strong>Secretary est un logiciel.</strong> Le traitement de vos emails,
        réunions et agenda est entièrement automatisé. Aucun collaborateur humain
        de Meoxa n'a accès à vos contenus dans le cadre normal de l'exploitation.
      </p>

      <h2>3. Catégories de données traitées</h2>
      <ul>
        <li>
          <strong>Données d'identification</strong> : nom, prénom, email, nom de
          l'organisation
        </li>
        <li>
          <strong>Données professionnelles</strong> : contenu des emails traités,
          enregistrements et transcriptions de réunions Teams, métadonnées d'agenda
        </li>
        <li>
          <strong>Données techniques</strong> : adresse IP, logs de connexion,
          identifiants de session, user-agent
        </li>
        <li>
          <strong>Données de facturation</strong> : moyen de paiement (via Stripe),
          historique de transactions
        </li>
      </ul>

      <h2>4. Finalités et bases légales</h2>
      <table>
        <thead>
          <tr>
            <th>Finalité</th>
            <th>Base légale</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Fourniture du service Secretary</td>
            <td>Exécution du contrat (art. 6.1.b RGPD)</td>
          </tr>
          <tr>
            <td>Facturation, comptabilité</td>
            <td>Obligation légale (art. 6.1.c)</td>
          </tr>
          <tr>
            <td>Amélioration technique (logs, monitoring d'erreurs)</td>
            <td>Intérêt légitime (art. 6.1.f)</td>
          </tr>
          <tr>
            <td>Support client</td>
            <td>Exécution du contrat</td>
          </tr>
        </tbody>
      </table>

      <h2>5. Sous-traitants</h2>
      <p>
        Dans le cadre du service, certains traitements sont délégués à des
        sous-traitants ultérieurs :
      </p>
      <table>
        <thead>
          <tr>
            <th>Sous-traitant</th>
            <th>Rôle</th>
            <th>Pays</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Anthropic PBC</td>
            <td>Génération de texte par IA (modèle Claude)</td>
            <td>États-Unis (CCT + DPA)</td>
          </tr>
          <tr>
            <td>Microsoft Ireland</td>
            <td>Graph API (accès à Outlook, Teams, OneDrive du Client)</td>
            <td>Irlande</td>
          </tr>
          <tr>
            <td>Voyage AI, Inc.</td>
            <td>Embeddings pour la mémoire contextuelle</td>
            <td>États-Unis (CCT + DPA)</td>
          </tr>
          <tr>
            <td>Stripe Payments Europe Ltd</td>
            <td>Traitement des paiements</td>
            <td>Irlande</td>
          </tr>
          <tr>
            <td>{"{{HEBERGEUR}}"}</td>
            <td>Hébergement des serveurs applicatifs</td>
            <td>Union européenne</td>
          </tr>
        </tbody>
      </table>
      <p>
        Un contrat de sous-traitance (DPA) détaillé est disponible sur demande et
        peut être généré depuis l'espace administration du Client.
      </p>

      <h2>6. Durée de conservation</h2>
      <ul>
        <li>
          <strong>Données d'authentification</strong> : pendant toute la durée du
          compte, supprimées 30 jours après résiliation
        </li>
        <li>
          <strong>Brouillons d'emails, transcriptions et CR</strong> : selon la
          politique de rétention configurée par le Client (0 à 3 650 jours)
        </li>
        <li>
          <strong>Logs de connexion et journaux d'audit</strong> : 12 mois
        </li>
        <li>
          <strong>Données de facturation</strong> : 10 ans (obligation comptable
          française)
        </li>
      </ul>

      <h2>7. Transferts hors Union européenne</h2>
      <p>
        Les données transférées à Anthropic et Voyage AI font l'objet de Clauses
        Contractuelles Types adoptées par la Commission européenne (décision 2021/914)
        et de DPA spécifiques. Aucune donnée n'est transférée vers un pays ne
        bénéficiant pas de garanties appropriées.
      </p>

      <h2>8. Vos droits</h2>
      <p>Conformément au RGPD, vous disposez des droits suivants :</p>
      <ul>
        <li><strong>Accès</strong> aux données vous concernant</li>
        <li><strong>Rectification</strong> des données inexactes</li>
        <li><strong>Effacement</strong> (« droit à l'oubli »)</li>
        <li><strong>Limitation</strong> du traitement</li>
        <li><strong>Portabilité</strong> — export ZIP de toutes vos données</li>
        <li><strong>Opposition</strong> au traitement</li>
        <li><strong>Retrait du consentement</strong> à tout moment</li>
      </ul>
      <p>
        Ces droits peuvent être exercés directement depuis votre espace Secretary
        (<code>/app/organization</code> → Données RGPD) ou en écrivant à{" "}
        <a href="mailto:dpo@meoxa.app">dpo@meoxa.app</a>.
      </p>
      <p>
        Vous disposez également du droit d'introduire une réclamation auprès de la
        Commission Nationale de l'Informatique et des Libertés (CNIL), 3 place de
        Fontenoy, TSA 80715, 75334 Paris Cedex 07 —{" "}
        <a href="https://www.cnil.fr" target="_blank" rel="noreferrer">cnil.fr</a>.
      </p>

      <h2>9. Sécurité</h2>
      <p>Meoxa met en œuvre les mesures techniques et organisationnelles suivantes :</p>
      <ul>
        <li>Chiffrement en transit (TLS 1.3) et au repos (AES-128 Fernet)</li>
        <li>Isolation multi-tenant au niveau base de données (Row-Level Security)</li>
        <li>Authentification multi-facteur (TOTP) disponible</li>
        <li>Journal d'audit immuable</li>
        <li>Sauvegardes chiffrées quotidiennes avec copie hors site</li>
      </ul>

      <h2>10. Cookies</h2>
      <p>
        L'utilisation de cookies est détaillée dans notre{" "}
        <a href="/legal/cookies">Charte cookies</a>.
      </p>

      <h2>11. Modifications</h2>
      <p>
        Cette politique peut évoluer. Toute modification substantielle sera notifiée
        au Client par email et mentionnée en tête du document.
      </p>
    </>
  );
}

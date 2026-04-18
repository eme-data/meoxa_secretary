import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Charte cookies — Secretary by Meoxa",
  description: "Utilisation des cookies par Secretary, l'application éditée par Meoxa.",
};

export default function CookiesPage() {
  return (
    <>
      <h1>Charte cookies</h1>
      <p className="text-sm text-slate-400">Dernière mise à jour : avril 2026</p>

      <h2>1. Qu'est-ce qu'un cookie ?</h2>
      <p>
        Un cookie est un petit fichier déposé sur votre terminal (ordinateur,
        smartphone) lors de la visite d'un site web. Il permet au site de reconnaître
        votre appareil et de stocker des informations relatives à votre session.
      </p>

      <h2>2. Cookies utilisés par Secretary</h2>
      <p>
        Secretary utilise <strong>uniquement des cookies strictement nécessaires</strong>
        au fonctionnement du service. Aucun cookie publicitaire, aucun traceur
        tiers pour la publicité comportementale.
      </p>

      <table>
        <thead>
          <tr>
            <th>Cookie</th>
            <th>Finalité</th>
            <th>Durée</th>
            <th>Type</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>access_token</code></td>
            <td>Authentification de la session utilisateur (JWT)</td>
            <td>30 minutes</td>
            <td>Nécessaire</td>
          </tr>
          <tr>
            <td><code>refresh_token</code></td>
            <td>Prolongation de la session sans re-login</td>
            <td>14 jours</td>
            <td>Nécessaire</td>
          </tr>
          <tr>
            <td><code>mfa_challenge</code> (sessionStorage)</td>
            <td>Stockage temporaire du challenge 2FA entre login et validation</td>
            <td>Session navigateur</td>
            <td>Nécessaire</td>
          </tr>
        </tbody>
      </table>

      <h2>3. Analytics respectueuse de la vie privée</h2>
      <p>
        Si un outil de mesure d'audience est activé (par exemple Plausible ou Umami),
        il est configuré en mode anonymisé : <strong>pas de cookie de suivi, pas de
        collecte d'identifiants personnels, pas de fingerprinting</strong>. Ces outils
        ne nécessitent pas de consentement explicite selon la recommandation de la CNIL.
      </p>

      <h2>4. Cookies tiers</h2>
      <p>
        Lors du paiement d'un abonnement, vous êtes redirigé vers la plateforme
        sécurisée <strong>Stripe</strong>, qui dépose ses propres cookies techniques
        nécessaires à la transaction. Consulter la politique Stripe :{" "}
        <a href="https://stripe.com/fr/privacy" target="_blank" rel="noreferrer">
          stripe.com/fr/privacy
        </a>.
      </p>
      <p>
        Lors de la connexion à Microsoft 365, vous êtes redirigé vers{" "}
        <strong>Microsoft</strong> pour le flux OAuth, qui dépose ses propres cookies.
      </p>

      <h2>5. Gestion des cookies</h2>
      <p>
        Les cookies strictement nécessaires ne peuvent pas être désactivés sans
        empêcher le service de fonctionner. Vous pouvez néanmoins les supprimer à
        tout moment depuis les préférences de votre navigateur :
      </p>
      <ul>
        <li>
          <a
            href="https://support.google.com/chrome/answer/95647"
            target="_blank"
            rel="noreferrer"
          >
            Chrome
          </a>
        </li>
        <li>
          <a
            href="https://support.mozilla.org/fr/kb/protection-renforcee-contre-pistage-firefox-ordinateur"
            target="_blank"
            rel="noreferrer"
          >
            Firefox
          </a>
        </li>
        <li>
          <a
            href="https://support.apple.com/fr-fr/guide/safari/sfri11471/mac"
            target="_blank"
            rel="noreferrer"
          >
            Safari
          </a>
        </li>
        <li>
          <a
            href="https://support.microsoft.com/fr-fr/microsoft-edge/supprimer-les-cookies-dans-microsoft-edge-63947406-40ac-c3b8-57b9-2a946a29ae09"
            target="_blank"
            rel="noreferrer"
          >
            Edge
          </a>
        </li>
      </ul>

      <h2>6. Contact</h2>
      <p>
        Pour toute question relative aux cookies :{" "}
        <a href="mailto:dpo@meoxa.app">dpo@meoxa.app</a>.
      </p>
    </>
  );
}

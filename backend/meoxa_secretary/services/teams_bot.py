"""DEPRECATED — remplacé par `MeetingRecordingService`.

Raison : les clients Office 365 Basic/Standard n'ont pas accès à Teams Premium,
donc pas d'accès API aux transcripts (`/me/onlineMeetings/{id}/transcripts`).
Un bot qui rejoint la réunion (Bot Framework + Azure Communication Services)
aurait fonctionné mais était trop complexe à provisionner pour ce cas d'usage.

Le pipeline actuel passe par OneDrive : quand le client active "enregistrement
auto + sous-titres live" dans Teams, les MP4/VTT sont déposés dans OneDrive,
notre souscription Graph nous notifie, et on traite via
`meoxa_secretary.services.meeting_recording.MeetingRecordingService`.

Ce module reste présent uniquement pour ne pas casser d'éventuels imports
historiques. Toute nouvelle intégration doit passer par `MeetingRecordingService`.
"""

import warnings

warnings.warn(
    "meoxa_secretary.services.teams_bot est déprécié — utiliser MeetingRecordingService",
    DeprecationWarning,
    stacklevel=2,
)

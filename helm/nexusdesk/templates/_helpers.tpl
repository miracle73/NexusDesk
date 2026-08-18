{{- define "nexusdesk.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "nexusdesk.labels" -}}
app.kubernetes.io/name: {{ include "nexusdesk.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

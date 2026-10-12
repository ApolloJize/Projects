"""Read an aggregate-only ADW view and request an OCI GenAI summary."""
import json
import oci
from healthlab.cloud import oracle, oci_client, setting
from healthlab.reporting import evidence_packet, prompt_for


def main():
    with oracle("REPORT_APP", "report-app") as db:
        rows = db.cursor().execute("SELECT ward,service_type,visits,event_count "
                                   "FROM pipeline_app.ward_summary ORDER BY ward,service_type").fetchall()
    if not rows:
        raise RuntimeError("No curated data. Check GoldenGate lag and run the OIC integration first.")
    packet = evidence_packet(rows)
    models = oci.generative_ai_inference.models
    region = setting("GENAI_REGION")
    client = oci_client(oci.generative_ai_inference.GenerativeAiInferenceClient,
        region=region, service_endpoint=f"https://inference.generativeai.{region}.oci.oraclecloud.com")
    response = client.chat(models.ChatDetails(
        compartment_id=setting("OCI_COMPARTMENT_OCID"),
        serving_mode=models.OnDemandServingMode(model_id=setting("GENAI_MODEL_ID")),
        chat_request=models.GenericChatRequest(
            messages=[models.UserMessage(content=[models.TextContent(text=prompt_for(packet))])],
            max_tokens=300, temperature=0.0)))
    print("Evidence:", json.dumps(packet, indent=2))
    print("\nGenerated summary (check it against the evidence):")
    for part in response.data.chat_response.choices[0].message.content:
        if part.type == "TEXT":
            print(part.text)


if __name__ == "__main__":
    main()

# Healthcare Medical Bookings

Sri Lanka's healthcare system is genuinely impressive in its reach. Free government hospitals exist across the island, and the country maintains strong health indicators by regional standards. However, navigating the system as a patient can be quite challenging.

## Challenges in the Healthcare System
- **Lack of guidance:** Most people do not know which type of doctor they need for a given set of symptoms, leading to visits to the wrong departments, referrals elsewhere, and wasted time.
- **Long queues:** Government hospital OPD queues in major cities begin forming before dawn and can involve thousands of patients.
- **Opaque private specialist availability:** Unless you call each clinic individually, it’s difficult to determine available specialists; channeling systems vary.
- **Medicine availability issues:** Prescriptions may only be partially filled at one pharmacy, requiring visits to multiple pharmacies.
- **Complex process for outside Colombo patients:** Finding the right doctor, booking appointments, and securing medicines involves multiple calls, uncertain travel plans, and significant delays.

## Lack of a Unified System
There is no integrated system connecting:
- Symptoms to medical specialties
- Specialties to available practitioners
- Practitioners to booking slots
- Prescriptions to nearby pharmacies with stock

## Potential AI Solution
An AI-powered conversational triage and navigation agent could significantly improve this process by:
1. Taking symptom input from patients.
2. Using a clinical knowledge base (not providing diagnoses) to identify the appropriate specialty.
3. Searching a RAG (Retrieval-Augmented Generation) index of verified private clinics, government hospital departments, and their scheduling channels to surface available options.
4. Integrating with a pharmacy availability tool—updated through crowdsourced reports or supplier data—to locate prescribed medicines at nearby stocked pharmacies.
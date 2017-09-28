import json
import time

json_data = """
[{"address": "Unit 7101 Box 9011 DPO AA 00059", "birth_date": "2002-12-14",
"column1": "7666826f-4696-46fe-92a2-8b2324fee7df", "column10": "c30ee91e-641a-49b5-981d-41e6cdb3afbf",
"column11": "0b6fd492-c9ff-4ca3-b723-aa37149b2610", "column12": "75d8d124-a9f3-438e-9e17-eed6e3c57bc2",
"column13": "ef1ec751-a8d6-4a95-9891-01adbd5cc47b", "column14": "fd6b3a79-4f58-4e40-a3ea-8660b10070a6",
"column15": "e275a7fa-3af0-4559-95ce-a61559b41e47", "column16": "c7af1758-0615-49a6-ae6a-eb268b5f52c5",
"column17": "94d9e6e1-9c22-48ce-a176-4d17d36e6112", "column18": "8ecbbc91-c444-49ff-91d9-78195fc0dfc2",
"column19": "2c95da3a-5f40-4611-be75-dd564a1dd6cb", "column2": "d20b613e-8250-4153-a1e4-6e2c53f889b4",
"column20": "85f43bd0-9d5b-494f-8d7a-3ced4e86cdf3", "column21": "01558cad-6784-4bec-aaa0-c318461d27c5",
"column22": "ecb03e89-1767-495d-8638-9cff10c2d43f", "column23": "800e97a9-679e-43e2-81bb-780870199887",
"column24": "c4e5e6f6-ab62-4b20-8939-6a1df92837c6", "column25": "9184b1ca-8334-4c7e-8e90-8365cac2a03f",
"column26": "b2b0c7f6-f9e5-4145-9b85-0c745d82844d", "column27": "6c2470c1-3849-47a6-9590-4ee575300333",
"column28": "6130f6ce-b8ed-45ce-899c-7fbe10ce7d14", "column29": "0c05edad-3612-422f-8d41-e3ff40f66e68",
"column3": "63b548cf-e60a-48f7-9d57-ac9103457ee6", "column30": "1ecbbd73-9927-4a53-8cc0-aa7a7d5f1ceb",
"column4": "d89561b6-a4b6-4ce7-93a7-6e9e2a00d7b6", "column5": "ffaeffa8-7b19-4e22-b215-b795e7b1395f",
"column6": "d76e93e9-e5a6-40eb-b51f-daea449ceba1", "column7": "3b7be58e-50fc-4a86-9424-876ef495dbee",
"column8": "1e782fce-f99b-4f84-b515-1b8aa653255a", "column9": "fd373043-cc8d-4508-8e69-57d34bf53ee3",
"company": "Kuphal, Crooks and Boyle", "credit_card": "4087318719187", "first_name": "Goldia",
"home_page": "http://bernhard.info/", "job": "Medical technical officer", "last_name": "Grant",
"telephone": "378.081.0527", "_id": "241142@example.com", "_deleted": false, "_updated": 0,
"_previous": null, "_ts": 1505336456740055, "_hash": "ce614a60b24640283f7f87d5b18b9ac1"}]
"""

entities = 0

start_time = time.monotonic()

for i in range(1000000):
    data = json.loads(json_data)
    entities += 1

end_time = time.monotonic()
time_used = end_time - start_time

if entities != 0:
    per_sec = entities / time_used
else:
    per_sec = 0

print("Done. Parsed %s entities in %d seconds (%d entities/sec)" % (entities, time_used, per_sec))

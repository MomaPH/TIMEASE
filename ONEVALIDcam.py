python scripts/generate_sample.py
python -c "
from timease.engine.models import SchoolData
data = SchoolData.from_json('timease/data/sample_school.json')
print(f'Teachers: {len(data.teachers)}')
print(f'Classes: {len(data.classes)}')
print(f'Rooms: {len(data.rooms)}')
print(f'Subjects: {len(data.subjects)}')
print(f'Curriculum entries: {len(data.curriculum)}')
print(f'Constraints: {len(data.constraints)}')
errors = data.validate()
if errors:
    for e in errors: print(f'ERROR: {e}')
else:
    print('All validations passed!')
"

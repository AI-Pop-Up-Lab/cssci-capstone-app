import './demographicChooser.css';

function DemographicChoiceDropdown({column, choices, onChange}) {

  return (
    <div className="DemographicChoiceDropdown">
        <p className="unbounded-weight300">{column}</p>
        <select onChange={(e) => onChange(e.target.value)} className="unbounded-weight300">
            {choices.map((choice) => (
                <option key={choice} value={choice}>
                    {choice}
                </option>
            ))}
        </select>
    </div>
  );
};

export default DemographicChoiceDropdown;
import { useEffect } from 'react';
import '../polling_results_modules/demographicChooser.css';

function DemographicChoiceDropdown({column, choices, onChange}) {

    let modifiedColumn;

    useEffect(() => {
        console.log(column)
    }, [column])

    if(column == 'vote 2030'){
        modifiedColumn = 'next GE vote'
    }else{
        modifiedColumn = column;
    }

    return (
    <div className="DemographicChoiceDropdown">
        <p className="unbounded-weight300">{modifiedColumn}</p>
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
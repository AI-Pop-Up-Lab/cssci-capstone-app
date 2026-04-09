import { useEffect } from 'react';
import axios from "axios";
import '../polling_results_modules/demographicChooser.css';

function DemographicChoiceDropdown({column, choices, onChange, columnToRename}) {

    let modifiedColumn;

    if(column == columnToRename){
        modifiedColumn = 'next GE vote'
    }else{
        modifiedColumn = column;
    }

    modifiedColumn = modifiedColumn.replace(/_/g, ' ')

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
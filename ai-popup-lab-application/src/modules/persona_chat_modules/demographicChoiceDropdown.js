// a dropdown option for a column in the demographic filter. updates parent data when option selected

import '../polling_results_modules/demographicChooser.css';

function DemographicChoiceDropdown({column, choices = [], onChange, columnToRename}) {

    let modifiedColumn;

    if(column === columnToRename){
        modifiedColumn = 'next GE vote'
    }else{
        modifiedColumn = column;
    }

    modifiedColumn = modifiedColumn.replace(/_/g, ' ')

    return (
    <div className="DemographicChoiceDropdown">
        <p className="unbounded-weight300">{modifiedColumn}</p>
        <select onChange={(e) => onChange(e.target.value)} className="unbounded-weight300">
            {choices.map((choice) => {
                const val = (choice && typeof choice === 'object') ? choice.value : choice;
                const label = (choice && typeof choice === 'object') ? choice.label : choice;
                return (
                    <option key={val} value={val}>
                        {label}
                    </option>
                );
            })}
        </select>
    </div>
  );
};

export default DemographicChoiceDropdown;
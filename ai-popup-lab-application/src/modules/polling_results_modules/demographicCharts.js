import './demographicCharts.css';



function DemographicCharts({pollingData, chosenDemographic}) {

  return (
    <div className="DemographicCharts">
      <p>Demographic charts, chosen demographics are {JSON.stringify(chosenDemographic)}</p>
    </div>
  );
};

export default DemographicCharts;
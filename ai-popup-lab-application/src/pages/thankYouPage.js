import './thankYouPage.css';
import spring from '../assets/svgs/spring.svg';

function ThankYouPage() {
  return (
    <div className="ThankYouPage unbounded-weight300">

      <img className="spring spring-top" src={spring} alt="" />

      <div className="thank-you-text">
        <h1>THANK YOU</h1>
        <h2>FOR SUPPORTING</h2>
        <h3>MECHANICAL POLLSTER</h3>
      </div>

      <img className="spring spring-bottom" src={spring} alt="" />

    </div>
  );
}

export default ThankYouPage;
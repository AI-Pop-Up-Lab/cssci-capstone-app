import './aboutPage.css';


function AboutPage() {
  return (
    <div className="AboutPage unbounded-weight300">
      <h1>About Us</h1>
      <p>This project is a collaboration between Computational Social Science and Cultural Data & AI students at the University of Amsterdam, under the supervision of Dr. Roberto Cerina.</p>
      <p>Opinion polls are at dire straits. Nonresponse rates are as high as 94%, and nonignorable nonresponse plagues the field. This means that it is increasingly more difficult to build get representative samples of public opinion. We believe getting a good sense of the public's views on politics is important for the quality of democracy. It informs researchers of societal trends, politicians of public sentiment, and citizens of where they stand relative to those around them.</p>
      <h2>The mechanical pollster</h2>
      <p>To this end, we have developed a mechanical pollster that uses data collected from national statistics offices and national election studies. We then use large language models to synthesise a persona who responds to a series of questions about political issues. These personas are sampled randomly from a pool of synthetic individuals, meaning we can generate a diverse set of opinions without some of the issues inherent in traditional polling methods. The sample is then post-stratified to produce a granular, area-level representation of public opinion on certain questions.</p>
      <p>This website also offers the ability to talk to the synthetic personas with a chat interface. This means that a user can gain insights into not just what a certain demographic of people think, but why they might hold those views, thus enriching the opinion poll beyond a simple answer.</p>
      <h2>The team</h2>
      <p>Ava Ali, Alexandra Roskam, Brendan Corcoran, Danielius Jonaitis, Jelle Tuls, Maddy Müller, Shriya Agrawal, Shanella Bleekemolen, Nhu Truong, Wenyi Xi, and Xuan Miao.</p>
    </div>
  );
}

export default AboutPage;
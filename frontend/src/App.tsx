import data from './mock/analysis.json'

function App() {
  return (
    <main>
      <h1>CodeAtlas — Mock Analysis</h1>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </main>
  )
}

export default App

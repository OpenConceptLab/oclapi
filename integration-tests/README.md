OpenConceptLab API Integration Tests

(replacement for ocl/integration_tests)

Tests are written with the [jest](https://jestjs.io/) framework in TypeScript using [node-fetch](https://github.com/bitinn/node-fetch) for API requests.

Requirements:
* npm (v6+)
or
* Docker (v18+)

Install dependencies with:

```bash
npm install
```

Run tests with:
```bash
npm t
```

Run test watching for changes with:
```bash
npm t -- --watch
```

Run tests against a different server (default: http://localhost:8000) with:
```bash
npm t --url=https://api.qa.openconceptlab.org/ --adminUser=admin --adminPassword=Admin123
```

Alternatively run tests in an isolated environment with Docker (used on CI):
```bash
docker build . --build-arg url=https://api.qa.openconceptlab.org/ --build-arg adminUser=admin --build-arg adminPassword=Admin123 --build-arg CACHEBUST=$(date +%s)
```

Run tests with Docker against a local server at http://localhost:8000 (default url):
```bash
docker build . --network="host" --build-arg CACHEBUST=$(date +%s)
```

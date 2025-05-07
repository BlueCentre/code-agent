const path = require('path');

module.exports = {
  entry: './src/index.js', // Updated entry point to use the modular React app
  output: {
    path: path.resolve(__dirname, 'dist'), // Output directory
    filename: 'main.js', 
  },
  mode: 'development', // Set to 'production' for optimized builds 
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env', '@babel/preset-react'],
          },
        },
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
};
